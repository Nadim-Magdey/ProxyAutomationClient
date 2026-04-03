from enum import Enum
from typing import Any, Dict


class StateResult(str, Enum):
    ProceedEvent = "proeedEvent"
    ProceedRequest = "proceedRequest"

class Events(str, Enum):
    BASIC_DETECTED = "BASIC_DETECTED"
    BASIC_FINISHED = "BASIC_FINISHED"
    FIXED_FINISHED= "FIXED_FINISHED"
class Phase(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    BOTH = "both"
    
    def __str__(self):
        return self.value
    
class FlowContext:
    def __init__(self):
        self.data: Dict[str, Any] = {}  # Shared state for actions
    
    def get(self, key: str, default=None):
        return self.data.get(key, default)
    
    def set(self, key: str, value: Any):
        self.data[key] = value
        
    def update(self, other: Dict[str, Any]):
        self.data.update(other)

class EngineEvent:
    def __init__(self, type: str, payload=None):
        self.type = type
        self.payload = payload

    def __str__(self):
        return f"EngineEvent(type={self.type}, payload={self.payload})"

class StepResult:
    def __init__(self, state, event=None):
        self.state = state
        self.event = event

    def __str__(self):
        return f"StepResult(state={self.state}, event={self.event})"
    