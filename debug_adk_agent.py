
import asyncio
import os
import sys
import json
import logging
import shutil
from pathlib import Path
from typing import Any

# Ensure we can import from the project root
sys.path.append(os.getcwd())

# Import ADK components
try:
    from google.adk.apps import App
    from google.adk.runners import InMemoryRunner
    from google.genai import types
    from google.adk.events import Event
except ImportError as e:
    print(f"Error: Failed to import google.adk. Ensure the environment is set up correctly.\n{e}")
    sys.exit(1)

# Import local agent factory
from benchmarks.answer_generators.adk_agents import create_workflow_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("debug_adk_agent")

def print_event(event: Event):
    """Prints an ADK event in a structured, readable format."""
    print("\n" + "="*80)
    print(f"EVENT: {event.author} (Invocation ID: {event.invocation_id})")
    
    content = event.content
    if not content:
        print("  (No Content)")
        return

    print(f"  Role: {content.role}")
    
    if content.parts:
        for i, part in enumerate(content.parts):
            print(f"  Part {i+1}:")
            if part.text:
                print(f"    Text: {part.text}")
            
            if part.function_call:
                print(f"    Function Call: {part.function_call.name}")
                print(f"      Args: {json.dumps(part.function_call.args, indent=2)}")
            
            if part.function_response:
                print(f"    Function Response: {part.function_response.name}")
                # Truncate long responses for readability
                resp_str = json.dumps(part.function_response.response, indent=2)
                if len(resp_str) > 1000:
                    resp_str = resp_str[:1000] + "... (truncated)"
                print(f"      Response: {resp_str}")
    print("="*80 + "\n")

import argparse

# ... imports ...

async def main():
    parser = argparse.ArgumentParser(description="Run a debug ADK agent.")
    parser.add_argument("prompt", nargs="?", default="List the files in the current directory. If it's empty, create a file named 'hello.txt' with the content 'Hello ADK!' and list it again.", help="The prompt to send to the agent.")
    args = parser.parse_args()

    # 1. Setup Workspace
    workspace_root = Path("tmp/debug_adk_workspace")
    if workspace_root.exists():
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True, exist_ok=True)
    
    print(f"Workspace created at: {workspace_root.resolve()}")
    
    # 2. Create Agent
    # We use a valid model name. gemini-2.0-flash-exp is a good default for testing.
    model_name = "gemini-2.0-flash-exp"
    agent = create_workflow_agent(workspace_root=workspace_root, model_name=model_name)
    
    print(f"Agent created: {agent.name}")

    # 3. Setup Runner
    app = App(name="debug_app", root_agent=agent)
    runner = InMemoryRunner(app=app)
    
    # 4. Create Session
    session = await runner.session_service.create_session(
        app_name=app.name, 
        user_id="debug_user"
    )
    
    # 5. Run with Prompt
    print(f"\nSending Prompt: {args.prompt}")
    
    try:
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=types.Content(role="user", parts=[types.Part(text=args.prompt)]),
        ):
            print_event(event)
            
    except Exception as e:
        logger.exception("An error occurred during execution:")

if __name__ == "__main__":
    if "GEMINI_API_KEY" not in os.environ:
        print("Warning: GEMINI_API_KEY is not set. The agent might fail.")
    
    asyncio.run(main())
