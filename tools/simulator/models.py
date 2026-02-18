
from pydantic import BaseModel
from typing import List, Optional, Callable, Any, Dict
import enum

class ActionType(str, enum.Enum):
    USER_PROMPT = "user_prompt"
    END_TEST = "end_test"

class ReactorAction(BaseModel):
    type: ActionType
    payload: str

class FileExpectation(BaseModel):
    path: str
    content: Optional[str] = None

class InteractiveSimulationCase(BaseModel):
    name: str
    initial_prompt: str
    max_turns: int = 10
    default_action: ReactorAction
    expected_files: List[FileExpectation] = []
    custom_verify: Optional[Callable[[str, Any], bool]] = None
    reactors: List[Any] = [] # Placeholder for now

class SimulationResult(BaseModel):
    success: bool
    transcript: str
    trace_logs: List[Any] = []
