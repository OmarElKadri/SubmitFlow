"""Quick test script to verify browser automation, LLM, and AgentQL integration"""
import base64
import json
import os
import logging
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
import agentql
from playwright.sync_api import sync_playwright

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Mock SaaS data
MOCK_SAAS_DATA = {
    "name": "TaskFlow Pro",
    "website_url": "https://taskflowpro.example.com",
    "description": "TaskFlow Pro is an AI-powered project management tool that helps teams collaborate efficiently, track progress in real-time, and automate repetitive workflows.",
    "category": "Productivity",
    "logo": "./assets/logo.png",
    "contact_email": "hello@taskflowpro.example.com"
}

# LLM prompt template
PROMPT_TEMPLATE = """You are an autonomous AI Browser Agent. Your goal is to navigate a website and successfully submit a SaaS product to its directory.

### INPUT DATA
Here is the data you must use:
{saas_data_json}

### INSTRUCTIONS
1. Analyze the attached screenshot of the current page.
2. **IMPORTANT**: If you see any cookie consent banner, popup, overlay, or modal that might block interactions, you MUST dismiss it first by clicking "Accept", "Accept All", "Close", "X", or similar buttons before proceeding with other actions.
3. Determine your current state:
   - **DISMISS_OVERLAY**: You see a cookie banner, consent popup, or modal that needs to be closed first.
   - **LOGIN_NEEDED**: You see a login screen.
   - **NAVIGATING**: You see a homepage/dashboard and need to find the "Submit" or "Add Tool" button.
   - **FILLING_FORM**: You see the submission form fields.
   - **SUCCESS**: You see a "Thank you" or "Submission Received" message.
4. Generate an AgentQL Query to find the necessary elements.
5. Define the actions to perform on those elements.

### RESPONSE FORMAT (STRICT JSON)
You must reply with VALID JSON only. Do not add markdown or explanations outside the JSON.

{{
  "thought": "Brief reasoning of what you see and why you are taking this action.",
  "status": "CONTINUE" or "DONE" or "FAILED",
  "workflow_state": "DISMISS_OVERLAY" or "LOGIN_NEEDED" or "NAVIGATING" or "FILLING_FORM" or "SUCCESS",
  "agentql_query": "The AgentQL query string, e.g., {{ accept_cookies_btn }} or {{ submit_btn }}",
  "actions": [
    {{
      "target_element_name": "matches a name in your agentql_query",
      "type": "fill" or "click" or "press",
      "value": "string to type (only for fill)" or "Enter (only for press)"
    }}
  ]
}}

### PRIORITY RULES
- Always dismiss cookie banners/overlays FIRST before any other action.
- Look for buttons like: "Accept", "Accept All", "Accept Cookies", "I Agree", "OK", "Close", "X", "Got it", "Dismiss".
- If an overlay is blocking the page, your agentql_query should target the dismiss/accept button.
"""


def capture_screenshot(page, screenshot_dir: Path, name: str = "current_page") -> str:
    """Capture screenshot and return base64 encoded string"""
    screenshot_dir.mkdir(exist_ok=True)
    screenshot_path = screenshot_dir / f"{name}.png"
    page.screenshot(path=str(screenshot_path), full_page=True)
    
    with open(screenshot_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def call_llm(screenshot_base64: str, saas_data: dict, history: list = None) -> dict:
    """Call LLM with screenshot and get structured response"""
    client = OpenAI(
        api_key=os.getenv("LLM_API_KEY"),
        base_url=os.getenv("LLM_BASE_URL")
    )
    
    history_text = ""
    if history:
        history_text = f"\n### HISTORY\nPrevious actions taken:\n{json.dumps(history, indent=2)}\n"
    
    prompt = PROMPT_TEMPLATE.format(saas_data_json=json.dumps(saas_data, indent=2))
    prompt = prompt.replace("### INSTRUCTIONS", f"{history_text}### INSTRUCTIONS")
    
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL"),
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
    print(f"\n--- LLM Raw Response ---\n{response_text}\n")
    
    # Parse JSON from response
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON: {e}")
        return {"status": "FAILED", "thought": "Could not parse LLM response"}


def execute_actions(page, agentql_query: str, actions: list) -> bool:
    """Execute actions using AgentQL to find elements"""
    if not actions:
        logger.info("No actions to execute")
        return True
    
    try:
        # Query elements using AgentQL
        logger.info(f"Executing AgentQL query: {agentql_query}")
        response = page.query_elements(agentql_query)
        
        if response is None:
            logger.error("AgentQL query returned None")
            return False
        
        # Execute each action
        for action in actions:
            target = action.get("target_element_name")
            action_type = action.get("type")
            value = action.get("value", "")
            
            logger.info(f"Executing action: {action_type} on {target} with value '{value}'")
            
            # Get the element from response using dot notation
            element = getattr(response, target, None)
            
            if element is None:
                logger.error(f"Element '{target}' not found in AgentQL response")
                continue
            
            # Execute the action
            if action_type == "fill":
                element.fill(value)
                logger.info(f"Filled '{target}' with: {value}")
            elif action_type == "click":
                try:
                    element.click(timeout=5000)
                except Exception:
                    # If normal click fails (e.g., overlay blocking), try force click
                    logger.warning(f"Normal click failed on '{target}', trying force click...")
                    element.click(force=True)
                logger.info(f"Clicked '{target}'")
            elif action_type == "press":
                page.keyboard.press(value)
                logger.info(f"Pressed key: {value}")
            else:
                logger.warning(f"Unknown action type: {action_type}")
            
            # Small delay between actions
            time.sleep(0.5)
        
        return True
    except Exception as e:
        logger.error(f"Error executing actions: {e}")
        return False


def test_full_workflow():
    """Test full workflow: Browser -> Screenshot -> LLM -> AgentQL -> Action"""
    print("=" * 70)
    print("Testing Full Workflow: Browser + LLM + AgentQL + Action Execution")
    print("=" * 70)
    
    # Configure AgentQL
    agentql.configure(api_key=os.getenv("AGENTQL_API_KEY"))
    
    screenshot_dir = Path("./screenshots")
    history = []
    max_iterations = 5
    
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)
        playwright_page = browser.new_page()
        
        # Wrap with AgentQL
        page = agentql.wrap(playwright_page)
        
        # Navigate to the directory
        url = "https://www.launchingnext.com/"
        print(f"\n[1] Navigating to: {url}")
        page.goto(url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        iteration = 0
        status = "CONTINUE"
        
        while status == "CONTINUE" and iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*70}")
            print(f"ITERATION {iteration}")
            print(f"{'='*70}")
            
            # Capture screenshot
            print(f"\n[{iteration}.1] Capturing screenshot...")
            screenshot_b64 = capture_screenshot(page, screenshot_dir, f"step_{iteration}")
            print(f"    Screenshot saved to {screenshot_dir}/step_{iteration}.png")
            
            # Call LLM
            print(f"[{iteration}.2] Calling LLM for page analysis...")
            llm_response = call_llm(screenshot_b64, MOCK_SAAS_DATA, history)
            
            print(f"\n--- LLM Analysis (Iteration {iteration}) ---")
            print(f"Thought: {llm_response.get('thought', 'N/A')}")
            print(f"Status: {llm_response.get('status', 'N/A')}")
            print(f"Workflow State: {llm_response.get('workflow_state', 'N/A')}")
            print(f"AgentQL Query: {llm_response.get('agentql_query', 'N/A')}")
            print(f"Actions: {json.dumps(llm_response.get('actions', []), indent=2)}")
            
            status = llm_response.get("status", "FAILED")
            
            if status == "CONTINUE":
                # Execute actions using AgentQL
                agentql_query = llm_response.get("agentql_query", "")
                actions = llm_response.get("actions", [])
                
                if agentql_query and actions:
                    print(f"\n[{iteration}.3] Executing actions via AgentQL...")
                    success = execute_actions(page, agentql_query, actions)
                    
                    if success:
                        print(f"    Actions executed successfully!")
                        # Add to history
                        history.append({
                            "iteration": iteration,
                            "thought": llm_response.get("thought"),
                            "actions": actions,
                            "result": "success"
                        })
                    else:
                        print(f"    Some actions failed!")
                        history.append({
                            "iteration": iteration,
                            "thought": llm_response.get("thought"),
                            "actions": actions,
                            "result": "partial_failure"
                        })
                    
                    # Wait for page to update
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)
                else:
                    print(f"\n[{iteration}.3] No actions to execute this iteration")
            
            elif status == "DONE":
                print(f"\n*** WORKFLOW COMPLETED SUCCESSFULLY ***")
            
            elif status == "FAILED":
                print(f"\n*** WORKFLOW FAILED ***")
        
        if iteration >= max_iterations:
            print(f"\n*** MAX ITERATIONS ({max_iterations}) REACHED ***")
        
        # Keep browser open for inspection
        print("\n[FINAL] Browser will stay open for 30 seconds for inspection...")
        print("        Press Ctrl+C to exit early.")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            pass
        
        browser.close()
    
    print("\n" + "=" * 70)
    print("Test completed!")
    print(f"Total iterations: {iteration}")
    print(f"Final status: {status}")
    print("=" * 70)


def test_browser_and_llm():
    """Simple test - just browser and LLM (no action execution)"""
    print("=" * 60)
    print("Testing Browser Automation + LLM Integration (No Actions)")
    print("=" * 60)
    
    screenshot_dir = Path("./screenshots")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        url = "https://www.launchingnext.com/"
        print(f"\n[1] Navigating to: {url}")
        page.goto(url)
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        
        print("[2] Capturing screenshot...")
        screenshot_b64 = capture_screenshot(page, screenshot_dir)
        print(f"    Screenshot saved to {screenshot_dir}/current_page.png")
        
        print("[3] Calling LLM for page analysis...")
        llm_response = call_llm(screenshot_b64, MOCK_SAAS_DATA)
        
        print("\n--- LLM Analysis ---")
        print(f"Thought: {llm_response.get('thought', 'N/A')}")
        print(f"Status: {llm_response.get('status', 'N/A')}")
        print(f"Workflow State: {llm_response.get('workflow_state', 'N/A')}")
        print(f"AgentQL Query: {llm_response.get('agentql_query', 'N/A')}")
        print(f"Actions: {json.dumps(llm_response.get('actions', []), indent=2)}")
        
        print("\n[4] Browser will stay open for 30 seconds for inspection...")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            pass
        
        browser.close()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


def test_api_endpoint():
    """Test FastAPI health endpoint"""
    import httpx
    
    print("\n--- Testing FastAPI Endpoints ---")
    
    with httpx.Client() as client:
        try:
            response = client.get("http://localhost:8000/health")
            print(f"GET /health: {response.status_code} - {response.json()}")
        except httpx.ConnectError:
            print("FastAPI server not running. Start it with: python main.py")


if __name__ == "__main__":
    import sys
    
    print("\nUsage:")
    print("  python test_run.py         - Run full workflow (Browser + LLM + AgentQL)")
    print("  python test_run.py simple  - Run simple test (Browser + LLM only)")
    print("  python test_run.py api     - Test API endpoints")
    print()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "api":
            test_api_endpoint()
        elif sys.argv[1] == "simple":
            test_browser_and_llm()
        else:
            test_full_workflow()
    else:
        # Default: run full workflow
        test_full_workflow()
