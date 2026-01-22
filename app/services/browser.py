"""Browser automation service using patchright and AgentQL"""
import base64
import logging
import time
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager
from collections import deque

import agentql
from patchright.sync_api import sync_playwright, Browser, Page

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# AgentQL rate limiter: 10 calls per minute
AGENTQL_RATE_LIMIT = 10
AGENTQL_RATE_WINDOW = 60  # seconds


class BrowserService:
    """Manages browser sessions and page interactions"""
    
    def __init__(self, headless: bool = None):
        self.headless = headless if headless is not None else settings.browser_headless
        self.screenshot_dir = Path(settings.screenshot_dir)
        self.screenshot_dir.mkdir(exist_ok=True)
        
        # Configure AgentQL
        agentql.configure(api_key=settings.agentql_api_key)
        
        # Rate limiting for AgentQL (10 calls per 60 seconds)
        self._agentql_call_times: deque = deque(maxlen=AGENTQL_RATE_LIMIT)
        
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
    
    def start(self):
        """Start browser session using Patchright with persistent context"""
        logger.info(f"Starting browser (headless={self.headless})")
        self._playwright = sync_playwright().start()

        if settings.browser_user_data_dir:
            user_data_dir = settings.browser_user_data_dir
        else:
            raise ValueError("BROWSER_USER_DATA_DIR is not set in .env file")

        # Patchright launches Chrome with remote debugging enabled. Chrome rejects remote debugging
        # when pointed at the *default* user data directory.
        norm = user_data_dir.replace("/", "\\").rstrip("\\").lower()
        if norm.endswith("\\google\\chrome\\user data") or norm.endswith("\\chromium\\user data"):
            raise ValueError(
                "BROWSER_USER_DATA_DIR is set to the default Chrome 'User Data' directory. "
                "Chrome blocks remote debugging for the default data dir, which causes Patchright to hang/timeout. "
                "Set BROWSER_USER_DATA_DIR to a dedicated folder (e.g. D:/Dev/AutoSaas/.patchright_profile)."
            )

        # Ensure the directory exists (especially if using a dedicated profile folder).
        try:
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        except Exception:
            # If it points to an invalid location, Patchright will fail with a clearer error below.
            pass

        logger.info(f"Using browser profile: {user_data_dir}")
        logger.info("Launching persistent Chrome context via Patchright...")
        logger.info(
            "If this hangs, ensure Chrome is not already running with the same profile. "
            "Consider using a dedicated profile directory (set BROWSER_USER_DATA_DIR to an empty folder)."
        )

        try:
            # Use launch_persistent_context for better anti-detection
            self._browser = self._playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                channel="chrome",
                headless=self.headless,
                no_viewport=True,
                timeout=60_000,
            )
        except Exception as e:
            logger.exception(f"Failed to launch browser context: {e}")
            # Ensure playwright is torn down on failure so callers don't hang on subsequent runs.
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
            raise

        playwright_page = self._browser.new_page()
        
        # Setup request interception for advanced stealth (Cloudflare bypass)
        def handle_route(route):
            headers = route.request.headers.copy()
            headers.update({
                'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"'
            })
            route.continue_(headers=headers)
        
        playwright_page.route('**/*', handle_route)
        
        self._page = agentql.wrap(playwright_page)
        logger.info("Browser started (Patchright + Chrome) with stealth headers and AgentQL wrapped")
    
    def stop(self):
        """Stop browser session"""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None
        logger.info("Browser stopped")
    
    @property
    def page(self) -> Page:
        """Get the current page"""
        if not self._page:
            raise RuntimeError("Browser not started. Call start() first.")
        return self._page
    
    def navigate(self, url: str, wait_for_idle: bool = True, timeout: int = 60000):
        """Navigate to a URL"""
        logger.info(f"Navigating to: {url}")
        self.page.goto(url, timeout=timeout)
        if wait_for_idle:
            try:
                self.page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                logger.warning("Networkidle timeout - continuing anyway")
        time.sleep(2)  # Small delay for dynamic content
    
    def capture_screenshot(self, name: str = "page") -> tuple[str, Path]:
        """
        Capture screenshot and return (base64_string, file_path)
        """
        screenshot_path = self.screenshot_dir / f"{name}.png"
        self.page.screenshot(path=str(screenshot_path), full_page=True)
        
        with open(screenshot_path, "rb") as f:
            base64_str = base64.standard_b64encode(f.read()).decode("utf-8")
        
        logger.debug(f"Screenshot saved: {screenshot_path}")
        return base64_str, screenshot_path
    
    def _wait_for_rate_limit(self):
        """Wait if necessary to respect AgentQL rate limit (10 calls/min)"""
        now = time.time()
        
        # Remove calls older than the rate window
        while self._agentql_call_times and now - self._agentql_call_times[0] > AGENTQL_RATE_WINDOW:
            self._agentql_call_times.popleft()
        
        # If we've hit the limit, wait until the oldest call expires
        if len(self._agentql_call_times) >= AGENTQL_RATE_LIMIT:
            wait_time = AGENTQL_RATE_WINDOW - (now - self._agentql_call_times[0]) + 1
            if wait_time > 0:
                logger.info(f"AgentQL rate limit reached. Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
        
        # Record this call
        self._agentql_call_times.append(time.time())
    
    def execute_actions(self, agentql_query: str, actions: list) -> bool:
        """
        Execute actions using AgentQL to find elements.
        
        Args:
            agentql_query: AgentQL query string (e.g., "{ submit_btn }")
            actions: List of action dicts with target_element_name, type, value
            
        Returns:
            True if all actions succeeded, False otherwise
        """
        if not actions:
            logger.info("No actions to execute")
            return True
        
        try:
            # Wait for rate limit before making AgentQL call
            self._wait_for_rate_limit()
            
            # Query elements using AgentQL
            logger.info(f"Executing AgentQL query: {agentql_query}")
            response = self.page.query_elements(agentql_query)
            
            if response is None:
                logger.error("AgentQL query returned None")
                return False
            
            # Execute each action
            for action in actions:
                target = action.get("target_element_name")
                action_type = action.get("type")
                value = action.get("value", "")
                
                logger.info(f"Executing: {action_type} on '{target}' with value '{value}'")
                
                # Get element from response
                element = getattr(response, target, None)
                
                if element is None:
                    logger.error(f"Element '{target}' not found in AgentQL response")
                    continue
                
                # Execute action
                if action_type == "fill":
                    element.fill(value)
                elif action_type == "click":
                    try:
                        element.click(timeout=5000)
                    except Exception:
                        logger.warning(f"Normal click failed on '{target}', trying force click")
                        element.click(force=True)
                elif action_type == "press":
                    self.page.keyboard.press(str(value))
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

                    # Note: this requires target to be an <input type=file> (or equivalent) element.
                    element.set_input_files(resolved if len(resolved) > 1 else resolved[0])
                else:
                    logger.warning(f"Unknown action type: {action_type}")
                    continue
                
                logger.info(f"Action completed: {action_type} on '{target}'")
                time.sleep(0.5)  # Small delay between actions
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing actions: {e}")
            return False
    
    def wait_for_navigation(self):
        """Wait for page to settle after navigation"""
        try:
            self.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass  # Timeout is okay, page might already be idle
        time.sleep(1)


@contextmanager
def browser_session(headless: bool = None):
    """Context manager for browser sessions"""
    browser = BrowserService(headless=headless)
    try:
        browser.start()
        yield browser
    finally:
        browser.stop()
