"""Job executor service - processes submission jobs using browser automation"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from uuid import UUID
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.submission_job import SubmissionJob, JobStatus
from app.models.submission_attempt import SubmissionAttempt, AttemptStatus
from app.models.agent_action_log import AgentActionLog
from app.models.saas_product import SaaSProduct
from app.models.directory import Directory
from app.services.browser import BrowserService
from app.services.llm_client import LLMClient
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class JobExecutor:
    """Executes submission jobs by automating browser interactions"""

    @staticmethod
    def _agentql_query_to_string(value: Any) -> str:
        """Coerce agentql_query into a string usable by AgentQL (page.query_elements).

        The prompt requests a string query like "{ submit_btn }", but LLMs sometimes return
        a dict of element names -> labels. In that case, we derive a query from the dict keys.
        """

        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            keys = [k for k in value.keys() if isinstance(k, str) and k.strip()]
            return "{ " + ", ".join(keys) + " }" if keys else ""
        if isinstance(value, list):
            keys = [str(x).strip() for x in value if str(x).strip()]
            return "{ " + ", ".join(keys) + " }" if keys else ""
        return ""

    @staticmethod
    def _normalize_actions(value: Any) -> list[dict]:
        """Normalize LLM 'actions' into a list[dict] for JSONB persistence and execution."""

        if value is None:
            return []
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                return []
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return []
        return [a for a in value if isinstance(a, dict)]
    
    def __init__(self, db: Session, headless: bool = False):
        self.db = db
        self.headless = headless
        self.llm_client = LLMClient()
        self.browser: Optional[BrowserService] = None
        self.max_iterations_per_attempt = 15
    
    def execute_job(self, job_id: UUID) -> bool:
        """
        Execute all pending attempts for a job.
        
        Args:
            job_id: The job UUID to execute
            
        Returns:
            True if job completed (all attempts processed), False if failed
        """
        # Get job
        job = self.db.query(SubmissionJob).filter(SubmissionJob.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        if job.status not in [JobStatus.NOT_STARTED, JobStatus.IN_PROGRESS, JobStatus.PAUSED]:
            logger.warning(f"Job {job_id} has status {job.status}, cannot execute")
            return False
        
        # Get product data
        product = self.db.query(SaaSProduct).filter(SaaSProduct.id == job.saas_product_id).first()
        if not product:
            logger.error(f"Product {job.saas_product_id} not found")
            return False
        
        saas_data = {
            "name": product.name,
            "website_url": product.website_url,
            "description": product.description,
            "category": product.category,
            "logo": product.logo,
            "contact_email": product.contact_email
        }
        
        # Update job status
        job.status = JobStatus.IN_PROGRESS
        if not job.started_at:
            job.started_at = datetime.now(timezone.utc)
        self.db.commit()
        
        logger.info(f"Starting job execution: {job_id}")
        logger.info(f"Product: {product.name}")
        
        # Start browser
        self.browser = BrowserService(headless=self.headless)
        try:
            self.browser.start()
        except Exception as e:
            logger.error(f"Browser failed to start: {e}")
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return False

        try:
            # Get pending attempts
            attempts = self.db.query(SubmissionAttempt).filter(
                SubmissionAttempt.job_id == job_id,
                SubmissionAttempt.status.in_([AttemptStatus.NOT_STARTED, AttemptStatus.IN_PROGRESS])
            ).all()
            
            for attempt in attempts:
                # Check if job was paused/stopped
                self.db.refresh(job)
                if job.status == JobStatus.PAUSED:
                    logger.info("Job paused, stopping execution")
                    break
                if job.status == JobStatus.FAILED:
                    logger.info("Job stopped, aborting execution")
                    break
                
                # Execute attempt
                success = self._execute_attempt(attempt, saas_data)
                
                # Update job counts
                if success:
                    job.completed_count += 1
                else:
                    job.failed_count += 1
                self.db.commit()
            
            # Check if job is complete
            self.db.refresh(job)
            if job.status == JobStatus.IN_PROGRESS:
                if job.completed_count + job.failed_count >= job.total_directories:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    logger.info(f"Job {job_id} completed: {job.completed_count} success, {job.failed_count} failed")
            
            return True
            
        except Exception as e:
            logger.error(f"Job execution error: {e}")
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now(timezone.utc)
            self.db.commit()
            return False
            
        finally:
            if self.browser:
                self.browser.stop()
    
    def _execute_attempt(self, attempt: SubmissionAttempt, saas_data: dict) -> bool:
        """
        Execute a single submission attempt.
        
        Args:
            attempt: The SubmissionAttempt to execute
            saas_data: Product data dict
            
        Returns:
            True if submission succeeded, False otherwise
        """
        # Get directory
        directory = self.db.query(Directory).filter(Directory.id == attempt.directory_id).first()
        if not directory:
            logger.error(f"Directory {attempt.directory_id} not found")
            return False
        
        logger.info(f"=" * 60)
        logger.info(f"Executing attempt for: {directory.name}")
        logger.info(f"URL: {directory.submission_url}")
        logger.info(f"=" * 60)
        
        # Update attempt status
        attempt.status = AttemptStatus.IN_PROGRESS
        attempt.started_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Navigate to directory
        url = directory.submission_url
        self.browser.navigate(url)
        
        history = []
        step_number = 0
        status = "CONTINUE"
        
        try:
            while status == "CONTINUE" and step_number < self.max_iterations_per_attempt:
                step_number += 1
                logger.info(f"\n--- Step {step_number} ---")
                
                # Capture screenshot
                screenshot_name = f"job_{attempt.job_id}_attempt_{attempt.id}_step_{step_number}"
                screenshot_b64, screenshot_path = self.browser.capture_screenshot(screenshot_name)
                
                # Call LLM
                llm_response = self.llm_client.analyze_page(
                    screenshot_base64=screenshot_b64,
                    saas_data=saas_data,
                    history=history
                )
                
                logger.info(f"LLM thought: {llm_response.get('thought', 'N/A')}")
                logger.info(f"Status: {llm_response.get('status', 'N/A')}")
                logger.info(f"Workflow: {llm_response.get('workflow_state', 'N/A')}")
                
                agentql_query_raw = llm_response.get("agentql_query")
                agentql_query_for_exec = self._agentql_query_to_string(agentql_query_raw)
                actions = self._normalize_actions(llm_response.get("actions", []))

                # Log to database
                action_log = AgentActionLog(
                    attempt_id=attempt.id,
                    step_number=step_number,
                    screenshot_path=str(screenshot_path),
                    llm_thought=llm_response.get("thought"),
                    workflow_status=llm_response.get("workflow_state"),
                    agentql_query=agentql_query_raw,
                    actions=actions,
                    success=True
                )
                self.db.add(action_log)
                self.db.commit()
                
                status = llm_response.get("status", "FAILED")
                
                if status == "CONTINUE":
                    # Execute actions
                    if agentql_query_for_exec and actions:
                        success = self.browser.execute_actions(agentql_query_for_exec, actions)
                        
                        # Update log with result
                        action_log.success = success
                        self.db.commit()
                        
                        if success:
                            history.append({
                                "step": step_number,
                                "thought": llm_response.get("thought"),
                                "actions": actions,
                                "result": "success"
                            })
                        else:
                            history.append({
                                "step": step_number,
                                "thought": llm_response.get("thought"),
                                "actions": actions,
                                "result": "failed"
                            })
                            action_log.error = "Action execution failed"
                            self.db.commit()
                        
                        # Wait for page update
                        self.browser.wait_for_navigation()
                    
                elif status == "DONE":
                    logger.info("Submission completed successfully!")
                    attempt.status = AttemptStatus.SUBMITTED
                    attempt.completed_at = datetime.now(timezone.utc)
                    self.db.commit()
                    return True
                    
                elif status == "FAILED":
                    logger.error(f"Submission failed: {llm_response.get('thought')}")
                    action_log.success = False
                    action_log.error = llm_response.get("thought")
                    self.db.commit()
            
            # Max iterations reached or failed
            if step_number >= self.max_iterations_per_attempt:
                logger.warning(f"Max iterations ({self.max_iterations_per_attempt}) reached")
            
            attempt.status = AttemptStatus.FAILED
            attempt.completed_at = datetime.now(timezone.utc)
            attempt.error_message = f"Failed after {step_number} steps"
            self.db.commit()
            return False
            
        except Exception as e:
            logger.error(f"Attempt execution error: {e}")
            attempt.status = AttemptStatus.FAILED
            attempt.completed_at = datetime.now(timezone.utc)
            attempt.error_message = str(e)
            self.db.commit()
            return False


def execute_job_sync(job_id: UUID, headless: bool = False):
    """
    Execute a job synchronously (for testing or background tasks).
    
    Args:
        job_id: Job UUID to execute
        headless: Run browser in headless mode
    """
    from app.db.session import SessionLocal
    
    db = SessionLocal()
    try:
        executor = JobExecutor(db, headless=headless)
        executor.execute_job(job_id)
    finally:
        db.close()
