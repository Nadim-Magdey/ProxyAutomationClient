from FlowEngine.Context import Context
from .inputs import Input
from typing import List
from .inputs import Input
from typing import List, Dict
import copy
from .inputs import Input
from typing import List, Dict
import copy

class InputsManager:
    """
    Manage, load, and store inputs
    """
    
    def __init__(self):
        self.inputs: List[Input] = []

    def loadInputsFromJson(self, json_data: Dict):
        """
        load inputs directly from a JSON object.
        exept the JSON in the format:
        {
            "inputs": [
                {"name": "username", "type": "text", "default": "guest", "constraints": {...}},
                {"name": "age", "type": "integer", "default": 18, "constraints": {...}}
            ]
        }
        """
        self.inputs.clear()  # clear previous inputs
        
        inputs_list = json_data.get("inputs", [])
        if not isinstance(inputs_list, list):
            raise ValueError("wrong JSON format: 'inputs' must be a list")

        for inp_params in inputs_list:
            self.inputs.append(Input(inp_params))
            
    def getInputs(self) -> List[Input]:
        """return a clone of the inputs list to prevent external modifications"""
        return copy.deepcopy(self.inputs)
    