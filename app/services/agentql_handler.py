"""AgentQL query execution handler"""
import agentql
from pathlib import Path
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


class AgentQLHandler:
    """Handles AgentQL query execution and element selection"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        agentql.configure(api_key=api_key)
    
    def wrap_page(self, playwright_page) -> Any:
        """Wrap a Playwright page with AgentQL capabilities"""
        return agentql.wrap(playwright_page)
    
    async def query_elements(self, page, query: str) -> Optional[Any]:
        """
        Execute an AgentQL query on the page and return the response.
        
        Args:
            page: AgentQL-wrapped page
            query: AgentQL query string, e.g., "{ submit_btn }"
            
        Returns:
            AQLResponseProxy with element locators accessible via dot notation
        """
        try:
            response = await page.query_elements(query)
            logger.info(f"AgentQL query executed: {query}")
            return response
        except Exception as e:
            logger.error(f"AgentQL query failed: {e}")
            return None
    
    async def get_element_by_prompt(self, page, prompt: str) -> Optional[Any]:
        """
        Get a single element by natural language description.
        
        Args:
            page: AgentQL-wrapped page
            prompt: Natural language description of element
            
        Returns:
            Playwright Locator or None
        """
        try:
            element = await page.get_by_prompt(prompt)
            logger.info(f"Element found by prompt: {prompt}")
            return element
        except Exception as e:
            logger.error(f"get_by_prompt failed: {e}")
            return None


async def execute_action(element, action_type: str, value: Any = "") -> bool:
    """Execute an action on an element.

    Args:
        element: Playwright Locator
        action_type: "fill", "click", "press", or "upload"
        value:
            - fill: string to type
            - press: key to press (e.g. "Enter")
            - upload: file path (string), list of file paths, or {"path": "..."} / {"paths": [...]}.

    Returns:
        True if successful, False otherwise
    """
    try:
        if element is None:
            logger.error("Cannot execute action: element is None")
            return False
            
        if action_type == "fill":
            await element.fill(value)
            logger.info(f"Filled element with: {value}")
        elif action_type == "click":
            await element.click()
            logger.info("Clicked element")
        elif action_type == "press":
            await element.press(str(value))
            logger.info(f"Pressed key: {value}")
        elif action_type in {"upload", "upload_file", "set_input_files"}:
            paths: list[str] = []

            if isinstance(value, str):
                paths = [value]
            elif isinstance(value, list):
                paths = [str(p) for p in value]
            elif isinstance(value, dict):
                if "path" in value:
                    paths = [str(value["path"]) ]
                elif "paths" in value and isinstance(value["paths"], list):
                    paths = [str(p) for p in value["paths"]]

            resolved: list[str] = []
            for p in paths:
                pp = Path(p)
                if not pp.is_absolute():
                    pp = (Path.cwd() / pp).resolve()
                if not pp.exists():
                    logger.error(f"Upload file not found: {pp}")
                    return False
                resolved.append(str(pp))

            if not resolved:
                logger.error("Upload action missing file path(s)")
                return False

            await element.set_input_files(resolved if len(resolved) > 1 else resolved[0])
            logger.info(f"Uploaded file(s): {resolved}")
        else:
            logger.error(f"Unknown action type: {action_type}")
            return False
        return True
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return False
