# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A utility script to execute an ADK Agent and capture its response and logs."""

import sys
import argparse
import importlib.util
import asyncio
import io
import traceback
import os
import json


async def main():
    parser = argparse.ArgumentParser(description="Run an ADK Agent.")
    parser.add_argument("--agent-file", required=True, help="Path to the agent definition file.")
    parser.add_argument("--prompt", required=True, help="The user prompt for the agent.")
    parser.add_argument("--model-name", required=True, help="The LLM model name.")
    parser.add_argument("--initial-state", default="{}", help="Initial session state as a JSON string.")
    
    args = parser.parse_args()

    try:
        # 1. Import ADK dependencies lazily inside the utility
        from google.adk.apps import App
        from google.adk.runners import InMemoryRunner
        from google.genai import types
    except ImportError:
        print("Error: Required ADK libraries not found in the current Python environment.")
        sys.exit(1)

    try:
        # 2. Dynamic Import of the Agent Module
        spec = importlib.util.spec_from_file_location("agent_mod", os.path.abspath(args.agent_file))
        if spec is None or spec.loader is None:
             raise ImportError(f"Could not load spec for {args.agent_file}")
             
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if not hasattr(module, "create_agent"):
            raise AttributeError(f"The module {args.agent_file} must define a 'create_agent(model_name: str)' function.")

        # 3. Initialize Agent and Infrastructure
        agent = module.create_agent(model_name=args.model_name)
        
        # Capture internal ADK logs (stdout/stderr)
        stdout = io.StringIO()
        stderr = io.StringIO()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = stdout
        sys.stderr = stderr

        try:
            app = App(name="external_run_app", root_agent=agent)
            runner = InMemoryRunner(app=app)
            
            # Parse state
            state_dict = json.loads(args.initial_state)
            
            session = await runner.session_service.create_session(
                app_name=app.name, 
                user_id="benchmark_user", 
                state=state_dict
            )

            # 4. Execute Run
            result_text = ""
            new_message = types.Content(role="user", parts=[types.Part(text=args.prompt)])
            
            async for event in runner.run_async(
                user_id=session.user_id, 
                session_id=session.id, 
                new_message=new_message
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            result_text += part.text

            # 5. Output Combined Result
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            print(f"Response: {result_text}")
            print("\n--- Logs ---")
            print(f"Stdout:\n{stdout.getvalue()}")
            print(f"Stderr:\n{stderr.getvalue()}")

        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    except Exception:
        print(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main())
