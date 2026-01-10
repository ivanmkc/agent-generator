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

from colorama import Fore, Style, init
from google.adk.events import Event

# Initialize colorama
init(autoreset=True)

class PrismaticLogger:
    """Logs events from the Prismatic multi-agent system with color coding."""

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

    def log_event(self, event: Event):
        """Logs an ADK Event to the console with appropriate styling."""
        author = event.author or "unknown"
        color = self.AGENT_COLORS.get(author, Fore.WHITE)
        
        prefix = f"{Style.BRIGHT}{color}[{author}]{Style.RESET_ALL}"
        
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
                # print(f"  Args: {part.function_call.args}") # Optional verbose

            if part.function_response:
                response_text = str(part.function_response.response)
                if len(response_text) > 500:
                    display_text = response_text[:500] + "... (truncated)"
                else:
                    display_text = response_text
                print(f"{prefix} {Fore.LIGHTGREEN_EX}⬅ Tool Result: {part.function_response.name}: {display_text}{Style.RESET_ALL}") 

    def log_system(self, message: str):
        """Logs a system message."""
        print(f"{Fore.LIGHTBLACK_EX}[System]: {message}{Style.RESET_ALL}")

    def log_error(self, message: str):
        """Logs an error message."""
        print(f"{Fore.RED}{Style.BRIGHT}[Error]: {message}{Style.RESET_ALL}")
