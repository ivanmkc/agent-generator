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

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Optional

import pexpect
from core.api_key_manager import ApiKeyManager
from google import genai
from .models import (
    ActionType,
    CommonActions,
    InteractiveSimulationCase,
    ReactorAction,
    SimulationResult,
    SimulationTranscript,
    SimulationTurn,
)

from .harness import (
    AntigravityHarness,
    BaseSimulatorHarness,
    ClaudeCodeHarness,
    CodexHarness,
    GeminiCliHarness,
    FakeCliHarness,
)


class LLMUserSimulant:
    def __init__(
        self,
        persona_script: str,
        api_key_manager: ApiKeyManager,
        model: str = "gemini-1.5-flash",
    ) -> None:
        self.persona_script = persona_script
        self.api_key_manager = api_key_manager
        self.model = model
        self.history: list[dict[str, str]] = []

    async def generate_reply(self, agent_output: str) -> str:
        prompt = (
            f"You are roleplaying as a user testing a CLI agent. Follow this persona script EXACTLY. "
            f"Do not refuse to answer. Do not say you are an AI. Do not provide explanations outside of the persona.\n\n"
            f"PERSONA SCRIPT:\n{self.persona_script}\n\n"
            f"--- INTERACTION LOG ---\n"
            f"Agent just said:\n{agent_output}\n\n"
            f"Current History:\n{self.history}\n\n"
            f"--- INSTRUCTION ---\n"
            f"Respond as the user in plain English text WITHOUT markdown code blocks or tool calls.\n"
            f"If the script is finished, say 'TEST_COMPLETE'.\n"
            f"Do not include any other text in your response."
        )

        try:
            async with self.api_key_manager.get_client(self.model) as client:
                response = await client.generate_content_async(prompt)
                reply = str(response.text).strip()
                self.history.append({"agent": agent_output, "user": reply})
                return reply
        except Exception as e:
            print(f"DEBUG: Simulant failed to generate text (blocked or empty): {e}")
            return "TEST_COMPLETE"


class SimulationRunner:
    @staticmethod
    def run(case, backend="gemini-cli", output_dir=None, api_key_manager: ApiKeyManager = None):
        """
        Standard orchestrator for a simulated user run using an InteractiveSimulationCase.
        """
        try:
            return asyncio.run(
                SimulationRunner.run_async(case, backend, output_dir, api_key_manager)
            )
        except Exception as e:
            print(f"Error running simulation: {e}")
            traceback.print_exc()
            return SimulationResult(
                case_name=case.name,
                backend=backend,
                success=False,
                transcript=SimulationTranscript(
                    case_name=case.name, backend=backend, turns=[]
                ),
                error_message=str(e),
            )

    @staticmethod
    async def run_async(
        case: InteractiveSimulationCase,
        backend="gemini-cli",
        output_dir=None,
        api_key_manager: ApiKeyManager = None,
    ) -> SimulationResult:
        py_dir = os.path.dirname(os.path.abspath(__file__))

        base_out = output_dir or os.path.join(py_dir, "outputs")
        run_out_dir = os.path.join(base_out, backend)
        os.makedirs(run_out_dir, exist_ok=True)

        if not api_key_manager:
            api_key_manager = ApiKeyManager(api_key_env_var="GEMINI_API_KEY")

        with tempfile.TemporaryDirectory() as tmp_dir:
            print(f"--- Starting Simulation: {case.name} ---")
            print(f"Sandbox: {tmp_dir}")

            # ... (setup code from original run method) ...

            case_slug = case.name.lower().replace(" ", "_")
            case_out_dir = os.path.join(run_out_dir, case_slug)
            os.makedirs(case_out_dir, exist_ok=True)

            log_path = os.path.join(case_out_dir, "session.log")

            if backend == "claude-code":
                harness = ClaudeCodeHarness(None, log_path)
            elif backend == "antigravity":
                harness = AntigravityHarness(None, log_path)
            elif backend == "codex":
                harness = CodexHarness(None, log_path)
            elif backend == "fake-cli":
                harness = FakeCliHarness(None, log_path)
            else:
                harness = GeminiCliHarness(None, log_path)

            base_cmd = harness.get_base_cmd(py_dir)

            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"

            cmd_str = " ".join(base_cmd)

            print(f"Executing with pexpect: {cmd_str}")
            child = pexpect.spawn(cmd_str, cwd=tmp_dir, env=env, encoding="utf-8", timeout=30)
            child.logfile_read = open(log_path, "a")

            success = False
            error_message = None
            transcript_turns = []

            try:
                turn_count = 0
                current_prompt = case.initial_prompt

                simulant = None
                if case.persona_script:
                    simulant = LLMUserSimulant(case.persona_script, api_key_manager)

                while turn_count < case.max_turns:
                    turn_count += 1
                    print(f"\n--- [Turn {turn_count}: SIMULANT] ---\n{current_prompt}\n")

                    # Expect the prompt first, before sending the line
                    # This is to capture the output of the previous command
                    await asyncio.get_event_loop().run_in_executor(
                        None, child.expect, [pexpect.TIMEOUT, pexpect.EOF, "gemini> "]
                    )
                    agent_text_before = child.before

                    await asyncio.get_event_loop().run_in_executor(
                        None, child.sendline, current_prompt
                    )

                    # Now expect the next prompt to get the agent's response
                    await asyncio.get_event_loop().run_in_executor(
                        None, child.expect, [pexpect.TIMEOUT, pexpect.EOF, "gemini> "]
                    )

                    agent_text = child.before
                    print(f"--- [Turn {turn_count}: AGENT] ---\n{agent_text[:500]}...\n")

                    selected_action = case.default_action

                    # Reactor logic here
                    for reactor in case.reactors:
                        if reactor.reactor_type == "regex":
                            if re.search(reactor.pattern, agent_text, re.IGNORECASE):
                                selected_action = reactor.action
                                break

                    if selected_action.type == ActionType.FAIL_TEST:
                        success = False
                        error_message = selected_action.payload
                        break

                    if selected_action.type == ActionType.END_TEST:
                        success = True
                        break

                    if selected_action == case.default_action and simulant:
                        current_prompt = await simulant.generate_reply(agent_text)
                    else:
                        current_prompt = selected_action.payload or CommonActions.DONT_KNOW.payload

                    transcript_turns.append(SimulationTurn(
                        turn_number=turn_count,
                        user_prompt=current_prompt,
                        agent_response=agent_text,
                        reactor_type_engaged="TODO",
                    ))


            except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF) as e:
                error_message = f"Simulation ended unexpectedly: {e}"
                success = False
            except Exception as e:
                error_message = f"Simulation Error: {e}"
                success = False
                traceback.print_exc()
            finally:
                child.close()

            # Verification logic here

            print(f"--- Simulation {case.name} Finished (Success: {success}) ---")
            if error_message:
                print(f"Error: {error_message}")
            print(f"See full log at: {log_path}\n")

            transcript = SimulationTranscript(
                case_name=case.name, backend=backend, turns=transcript_turns
            )

            return SimulationResult(
                case_name=case.name,
                backend=backend,
                success=success,
                transcript=transcript,
                extracted_output=None,
                error_message=error_message,
            )
