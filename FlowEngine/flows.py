from .FlowManager import Flow, OptionalFlow
from .Context import Context

from ProxyEngine.Rules import DetectRule, EditHeaders, ExtractHeaderVariable, RulePhase, Methods

def detect_callback(result, context: Context):
    data = result.getData()
    context.store("url", data["url"])
    context.store("method", data["method"])
    
    
def extract_header_callback(result, context: Context):
    data = result.getData()
    context.store(data["header_key"], data["header_value"])
    