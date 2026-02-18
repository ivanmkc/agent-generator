
import asyncio
import pexpect
from typing import Optional
from tools.simulator.models import InteractiveSimulationCase, SimulationResult
from core.api_key_manager import ApiKeyManager

class SimulationRunner:
    def __init__(self, case: InteractiveSimulationCase, backend_command: str, api_key_manager: Optional[ApiKeyManager] = None):
        self.case = case
        self.backend_command = backend_command
        self.api_key_manager = api_key_manager

    async def run_async(self) -> SimulationResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.run)

    def run(self) -> SimulationResult:
        transcript = ""
        try:
            child = pexpect.spawn(self.backend_command, encoding='utf-8')
            transcript += child.before
            child.sendline(self.case.initial_prompt)

            # This is a simplified interaction loop
            for i in range(self.case.max_turns):
                # A more sophisticated implementation would use reactors to decide the next action
                child.expect(r'>|\$') # Simple prompt detection
                transcript += child.before
                if self.case.default_action.type == "end_test":
                    break
                child.sendline(self.case.default_action.payload)

            # Simplified verification
            success = True # Assume success for now
            
            return SimulationResult(
                success=success,
                transcript=transcript,
            )
        except Exception as e:
            return SimulationResult(
                success=False,
                transcript=transcript + f"
SIMULATOR ERROR: {e}",
            )

# Placeholder for LLMReactor and LLMUserSimulant
class LLMUserSimulant:
    def __init__(self, api_key_manager: Optional[ApiKeyManager] = None):
        self.api_key_manager = api_key_manager

    async def generate_reply(self, prompt: str, model: str):
        if not self.api_key_manager:
            # fallback logic
            return "mocked_reply"
        async with self.api_key_manager.get_client(model) as client:
            response = await client.generate_content_async(prompt)
            return response.text

class LLMReactor:
    def __init__(self, api_key_manager: Optional[ApiKeyManager] = None):
        self.api_key_manager = api_key_manager
