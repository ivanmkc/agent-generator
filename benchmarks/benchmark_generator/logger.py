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

"""Custom logger for Prismatic Generator events."""

import datetime
import json
from pathlib import Path
from typing import Optional, Any, Dict
from colorama import Fore, Style, init
from google.adk.events import Event

# Initialize colorama
init(autoreset=True)

class PrismaticLogger:
    """Logs events from the Prismatic multi-agent system with color coding and structured file tracing."""

    AGENT_COLORS = {
        "Auditor": Fore.YELLOW,
        "Observer": Fore.CYAN,
        "Saboteur": Fore.RED,
        "Referee": Fore.MAGENTA,
        "Critic": Fore.BLUE,
        "Assembler": Fore.GREEN,
        "Coordinator": Fore.LIGHTBLACK_EX,
        "model": Fore.WHITE,
        "user": Fore.LIGHTWHITE_EX
    }

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir
        self.trace_file = None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.trace_file = self.output_dir / "generation_trace.jsonl"

    def _timestamp(self):
        return datetime.datetime.now().strftime("%H:%M:%S")

    def log_trace(self, event_type: str, details: Dict[str, Any]):
        """Logs a structured event to the trace file."""
        if not self.trace_file:
            return
            
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": event_type,
            "details": details
        }
        
        try:
            with open(self.trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"{Fore.RED}Failed to write to trace log: {e}{Style.RESET_ALL}")

    def log_event(self, event: Event):
        """Logs an ADK Event to the console with appropriate styling."""
        author = event.author or "unknown"
        color = self.AGENT_COLORS.get(author, Fore.WHITE)
        ts = self._timestamp()
        
        prefix = f"{Style.DIM}{ts}{Style.RESET_ALL} {Style.BRIGHT}{color}[{author}]{Style.RESET_ALL}"
        
        if not event.content or not event.content.parts:
            return

        for part in event.content.parts:
            if part.text:
                # Truncate very long text but keep enough context
                text = part.text.strip()
                if not text:
                    continue
                
                # If text is a JSON block, maybe just show a summary?
                # For now, just print it.
                print(f"{prefix}: {text}")
            
            if part.function_call:
                print(f"{prefix} {Fore.LIGHTYELLOW_EX}➔ Tool Call: {part.function_call.name}{Style.RESET_ALL}")
                print(f"{Style.DIM}   Arguments: {part.function_call.args}{Style.RESET_ALL}")
                print(f"{Style.DIM}   ... Waiting for result ...{Style.RESET_ALL}")

            if part.function_response:
                response_text = str(part.function_response.response)
                if len(response_text) > 500:
                    display_text = response_text[:500] + "... (truncated)"
                else:
                    display_text = response_text
                print(f"{prefix} {Fore.LIGHTGREEN_EX}⬅ Tool Result: {part.function_response.name}: {display_text}{Style.RESET_ALL}") 

    def log_system(self, message: str):
        """Logs a system message."""
        ts = self._timestamp()
        print(f"{Style.DIM}{ts}{Style.RESET_ALL} {Fore.LIGHTBLACK_EX}[System]: {message}{Style.RESET_ALL}")

    def log_info(self, message: str):
        """Logs an info message."""
        ts = self._timestamp()
        print(f"{Style.DIM}{ts}{Style.RESET_ALL} {Fore.CYAN}[Info]: {message}{Style.RESET_ALL}")

    def log_error(self, message: str):
        """Logs an error message."""
        ts = self._timestamp()
        print(f"{Style.DIM}{ts}{Style.RESET_ALL} {Fore.RED}{Style.BRIGHT}[Error]: {message}{Style.RESET_ALL}")
