"""OpenAI-compatible LLM client with vision capabilities"""
import base64
import json
import logging
from pathlib import Path
from openai import OpenAI
from app.config import get_settings
from app.prompts.browser_agent import BROWSER_AGENT_PROMPT

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMClient:
    """LLM client for analyzing screenshots and deciding actions"""
    
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url
        )
        self.model = settings.llm_model
    
    def analyze_page(
        self,
        screenshot_base64: str,
        saas_data: dict,
        credentials: dict = None,
        history: list = None
    ) -> dict:
        """
        Analyze a page screenshot and return structured actions.
        
        Args:
            screenshot_base64: Base64 encoded screenshot
            saas_data: SaaS product data dict
            credentials: Optional login credentials
            history: List of previous actions taken
            
        Returns:
            Dict with thought, status, workflow_state, agentql_query, actions
        """
        # Build prompt
        history_log = json.dumps(history or [], indent=2)
        credentials_json = json.dumps(credentials or {}, indent=2)
        saas_data_json = json.dumps(saas_data, indent=2)
        
        prompt = BROWSER_AGENT_PROMPT.format(
            saas_data_json=saas_data_json,
            credentials_json=credentials_json,
            history_log=history_log
        )
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1024
            )
            
            response_text = response.choices[0].message.content
            logger.debug(f"LLM raw response: {response_text}")
            
            # Parse JSON from response
            return self._parse_response(response_text)
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {
                "status": "FAILED",
                "thought": f"LLM call failed: {str(e)}",
                "workflow_state": "FAILED",
                "agentql_query": "",
                "actions": []
            }
    
    def _parse_response(self, response_text: str) -> dict:
        """Parse LLM response JSON, handling markdown code blocks"""
        try:
            # Try to extract JSON if wrapped in markdown
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "status": "FAILED",
                "thought": "Could not parse LLM response as JSON",
                "workflow_state": "FAILED",
                "agentql_query": "",
                "actions": []
            }


def encode_screenshot(screenshot_path: Path) -> str:
    """Encode a screenshot file to base64"""
    with open(screenshot_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")
