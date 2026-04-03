from typing import Dict, Any


class ActionResult:
    def __init__(self, success=True, message=None):
        """
        success: bool - if action succeeded
        message: str  - feedback for GUI
        proxy_rule: dict - request to generate a proxy rule
        """
        self.success = success
        self.message = message
        self.data = Dict[str, Any]
        
    def setData(self, data:Dict[str,str]):
        self.data = data
    
    def getData(self)->Dict:
        return self.data
    