"""AgentQL query execution handler"""
import agentql
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


async def execute_action(element, action_type: str, value: str = "") -> bool:
    """
    Execute an action on an element.
    
    Args:
        element: Playwright Locator
        action_type: "fill", "click", or "press"
        value: Value for fill or key for press
        
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
            await element.press(value)
            logger.info(f"Pressed key: {value}")
        else:
            logger.error(f"Unknown action type: {action_type}")
            return False
        return True
    except Exception as e:
        logger.error(f"Action execution failed: {e}")
        return False
