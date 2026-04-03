from typing import Dict, Optional, Any
from enum import Enum


class InputTypes(str, Enum):
    TEXT = "text"
    NUMBER = "number"


class Input:
    def __init__(self, params: Dict[str, Any]):
        self.params = params

    def name(self) -> str:
        return self.params["name"]

    def type(self) -> InputTypes:
        return InputTypes(self.params.get("type", "text"))

    def default(self) -> Optional[Any]:
        return self.params.get("default")

    def placeholder(self) -> str:
        return self.params.get("placeholder", self.name())

    def constraints(self) -> Dict[str, Any]:
        return self.params.get("constraints", {})
