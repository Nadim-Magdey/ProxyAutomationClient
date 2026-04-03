from __future__ import annotations
from abc import ABC, abstractmethod
import re
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from mitmproxy.http import HTTPFlow
from Api import end_ppoints
from Api.Client import ApiClient
from Api.data.AuthEngine.AuthManager import AuthManager
from .custom_types import Phase, FlowContext
from .helpers import resolve_value
from Api.end_ppoints import ApiEndpoints

class ActionResult:
    def __init__(self, continue_flow: bool = True, stop_flow: bool = False):
        self.continue_flow = continue_flow
        self.stop_flow = stop_flow

    @staticmethod
    def continue_():
        return ActionResult(continue_flow=True)

    @staticmethod
    def stop():
        return ActionResult(continue_flow=False, stop_flow=True)

class Action(ABC):
    name: str = "base_action"
    def __init__(
        self,
        *,
        url_regex: str,
        phase: Phase = Phase.REQUEST,
        methods: list[str] | None = None,
        params: Dict[str, Any] | None = None,
        log:bool = False
    ):
        self.url_regex = url_regex
        self.phase = phase
        self.methods = methods
        self.params = params or {}
        self.log : bool = log
    def supports_phase(self, phase: Phase) -> bool:
        return self.phase in (Phase.BOTH, phase)

    def check(self, httpFlow: HTTPFlow) -> bool:
        """
        check if the action should be executed, based on phase, url regex and method
        returns True if the action should be executed
        """
        # Phase validation
        if self.phase == Phase.REQUEST and httpFlow.response is not None:
            # print(f"flow {httpFlow} does not match phase {self.phase}")
            return False

        if self.phase == Phase.RESPONSE and httpFlow.response is None:
            # print(f"flow {httpFlow} does not match phase {self.phase}")
            return False

        # URL ALWAYS comes from request
        url = httpFlow.request.url
        # print(f"real url {url}")
        # print(f"regex {self.url_regex}")

        if not re.search(self.url_regex, url):
            # print(f"Action {self.name} does not match URL {url}")
            return False

        # Method check only makes sense for request
        if self.methods:
            method = httpFlow.request.method
            if method not in self.methods:
                # print(f"Action {self.name} does not match method {method}")
                return False
                
        print(f"action {self.name} matches {url}")
        
        return True

    def log_if_needed(self,service_name, logType, info):
        """
        logs the action if log  param is true
        """
        print(f"parans {self.params}")
        try:
            is_logging = self.params.get("log")
            if is_logging:

                user_token = AuthManager.getInstance().getToken()

                api_client = ApiClient("http://127.0.0.1:8000", user_token)
                api_endpoints = ApiEndpoints(api_client)      
                return api_endpoints.log(
                    service_name,
                        logType,
                        info 
                )
        except Exception as e:
            print(f"Error logging: {e}")

    @abstractmethod
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        
        ...

class DetectAction(Action):
    name: str = "detect"

    """
    Detects if the flow should be activated based on URL regex.
    """
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        pass
    
class RejectAction(Action):
    name: str = "reject"

    """
    Rejects the request or response by killing the flow or setting a 403 status.
    """
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        "reject incoming or outgoing request/response"
        if self.phase == Phase.REQUEST:
            http_flow.response = HTTPFlow.make_response(
                http_flow.request,
                status_code=403,
                content=b"Request Rejected by RejectAction"
            )
        elif self.phase == Phase.RESPONSE:
            http_flow.response.status_code = 403

        return ActionResult.stop()

class RedirectAction(Action):
    name: str = "redirect"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        """redirect request to a different URL"""
        dist = self.params.get("destination")
        http_flow.request.url = dist
        return ActionResult.continue_()

class ForwardAction(Action):
    name: str = "forward"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        """do nothing"""
        return ActionResult.continue_()

class RemoveBodyElementAction(Action):

    name: str = "remove_body_element"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        """"Remove body element according to regix"""
        element_regex = self.params.get("element_regex")
        target = http_flow.request.content if self.phase == Phase.REQUEST else http_flow.response.content
        # remove element_regix from target 
        
        new_content = re.sub(element_regex, "", target.decode('utf-8'))
        #change target content
        if self.phase == Phase.REQUEST:
            http_flow.request.set_text(new_content)
        else:
            http_flow.response.set_text(new_content)
        return ActionResult.continue_()

class ChangeBodyAction(Action):
    name: str = "change_body"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        content = resolve_value(self.params.get("content", ""), ctx)

        if self.phase == Phase.REQUEST:
            http_flow.request.set_text(content)
        else:
            http_flow.response.set_text(content)
        return ActionResult.continue_()

class ExtractBodyElementAction(Action):
    name: str = "extract_body_element"
    """
    Extracts a body element matching a regex and stores it in context data
    under the specified return_name.
    """
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        try:

            element_regex = self.params.get("element_regix")
            return_name = self.params.get("return_name")
            target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response
            target_body = ""
            if hasattr(target, "get_text"):
                target_body = target.get_text()
                match = re.search(element_regex, target_body)
                if match:
                    extracted_value = match.group(1)
                    ctx.data[return_name] = extracted_value

        except Exception as e:
            print(f"Error extracting body element: {e}")
            
        return ActionResult.continue_()

class EditBodyAction(Action):
    name: str = "edit_body"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        find = self.params.get("element_regix")
        replace = resolve_value(self.params.get("new_value", ""), ctx)
        
        
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response
        if hasattr(target, "get_text") and hasattr(target, "set_text"):
            body = target.get_text()
            new_body = re.sub(find, replace, body)
            target.set_text(new_body)

        return ActionResult.continue_()
        
class EditHeadersAction(Action):
    name: str = "edit_headers"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        new_value = resolve_value(self.params.get("new_value", ""), ctx)

        header_key = self.params.get("header_key")
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response

        if hasattr(target, "headers"):
            target.headers[header_key] = new_value
        
        return ActionResult.continue_()
    
class ExtractHeaderVariableAction(Action):
    name: str = "extract_header"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        key = self.params.get("header_key")
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response

        if hasattr(target, "headers"):
            value = target.headers.get(key)
            ctx.data[key] = value
        return ActionResult.continue_()

class RemoveHeaderAction(Action):
    name: str = "remove_header"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        key = self.params.get("header_key")
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response
        if hasattr(target, "headers") and key in target.headers:
            del target.headers[key]
        return ActionResult.continue_()


class ExtractQueryAction(Action):
    name: str = "extract_query"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        key = self.params.get("query_key")
        url = http_flow.request.url if self.phase == Phase.REQUEST else http_flow.response.url
        parsed = urlparse(url)        
        queries = parse_qs(parsed.query)
        if key in queries:
            ctx.data[key] = queries[key][0]

        return ActionResult.continue_()

class EditQueryAction(Action):
    name: str = "edit_query"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        key = self.params.get("query_key")
        new_value = resolve_value(self.params.get("new_value"),ctx)
        url = http_flow.request.url if self.phase == Phase.REQUEST else http_flow.response.url
        parsed = urlparse(url)
        queries = parse_qs(parsed.query)
        
        if key in queries:
            queries[key] = [new_value]
            new_query = urlencode(queries, doseq=True)
            new_url = urlunparse(parsed._replace(query=new_query))
            http_flow.request.url = new_url
            ctx.data[key] = new_value
        return ActionResult.continue_()

class RemoveQueryAction(Action):
    name: str = "remove_query"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        key = self.params.get("query_key")
        url = http_flow.request.url if self.phase == Phase.REQUEST else http_flow.response.url
        parsed = urlparse(url)
        queries = parse_qs(parsed.query)
        if key in queries:
            del queries[key]
            new_query = urlencode(queries, doseq=True)
            new_url = urlunparse(parsed._replace(query=new_query))
            http_flow.request.url = new_url
        return ActionResult.continue_()

class ApplyFunctionAction(Action):
    name: str = "apply_function"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        client = ApiClient.GetInstance("http://127.0.0.1:8000", "feb3e627a588e58f81dfef7e986a5b8c1051ca93")
        end_ppoints = ApiEndpoints(client)
        # func_name = self.params.get("function")
        # func = getattr(end_ppoints, func_name)
        # func(http_flow.request)
        # return ActionResulat.continue_()

class ChangeStatusCodeAction(Action):
    name:str = "change_status_code"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        status_code = int(self.params.get("status_code"))

        http_flow.response.status_code = status_code
        return ActionResult.continue_()

class InsertHeaderKey(Action):
    name: str = "insert_header"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        key = self.params.get("header_key")
        value = self.params.get("header_value")
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response
        if hasattr(target, "headers"):
            target.headers[key] = value
            
        return ActionResult.continue_()

class CustomDetectAction(Action):
    name: str = "custom_detect"
    """
    take schama json in form 
     "type": "object",
            "properties": {
              "action": { "const": "customDetect" },
              "log": { "type": "boolean" },
              "params": { "$ref": "#/definitions/customDetectParams" }
            },
            "required": ["action", "params"],
            "additionalProperties": true
          }
          ,
    "customDetectParams":{
      "type": "object",
      "properties": {
        "method": { "type": "string" },
        "url_regix": { "type": "string" },
        "phase": { "type": "string" },
        "regix_type": { "type": "string", "enum": ["query", "header", "body"] },
        "type": { "type": "string", "enum": ["fixed", "variable"] },
        "value" : { "type": "string" }

      },
      "required": ["method", "url_regix", "phase", "regix_type", "value"],
      "additionalProperties": false
    }
    """
        
    def check(self, httpFlow: HTTPFlow) -> bool:
        # run normal validation first
        if not super().check(httpFlow):
            return False
        print(f"recieved value {self.params.get("value")}")
        target = httpFlow.request if self.phase == Phase.REQUEST else httpFlow.response
        
        try:
            # get source based on regix_type
            if self.params.get("regix_type") == "query":
                source = target.query
                source = "&".join([f"{k}={v}" for k, v in source.items()])

            elif self.params.get("regix_type") == "header":
                source = target.headers
                source = "\n".join([f"{k}:{v}" for k, v in source.items()])

            elif self.params.get("regix_type") == "body":
                source = target.get_text()

            else:
                return False
            
            # regex check
            if not re.search(self.params.get("value"), source):
                return False

            print(f"customDetect {self.name} matched")
            return True
        
        except Exception as e:
            print(f"Error checking customDetect {self.name}: {e}")
            return False
        # return super().check(httpFlow)
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:

        return ActionResult.continue_()

# handle url params
"""
    "extractUrlParamsParams":{
            "type": "object",
      "properties": {
        "method": { "type": "string" },
        "url_regix": { "type": "string" },
        "phase": { "type": "string" },
        "param_regix": { "type": "string" },
        "return_name" : { "type": "string" }
      },
      "required": ["method", "url_regix", "phase", "param_regix", "valureturn_namee"],
      "additionalProperties": false
    },
      "editUrlParamParams":{
        "type": "object",
      "properties": {
        "method": { "type": "string" },
        "url_regix": { "type": "string" },
        "phase": { "type": "string" },
        "param_regix": { "type": "string" },
        "new_value" : { "type": "string" }
      },
      "required": ["method", "url_regix", "phase", "param_regix", "new_value"],
      "additionalProperties": false
    },
        "removeUrlParamParams":{
        "type": "object",
      "properties": {
        "method": { "type": "string" },
        "url_regix": { "type": "string" },
        "phase": { "type": "string" },
        "param_regix": { "type": "string" }
      },
      "required": ["method", "url_regix", "phase", "param_regix"],
      "additionalProperties": false
    }
"""
class ExtractURlParam(Action):
    name: str = "extract_url_param"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        param_regix = self.params.get("param_regix")
        return_name = self.params.get("return_name")
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response

        try:
            match = re.search(param_regix, target.url)
            if match:
                extracted_value = match.group(1)
                ctx.data[return_name] = extracted_value

        except Exception as e:
            print(f"Error extracting url param: {e}")

        return ActionResult.continue_()    

class EditUrlParam(Action):
    name: str = "edit_url_param"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        param_regix = self.params.get("param_regix")
        new_value = resolve_value(self.params.get("new_value", ""), ctx)
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response

        try:
            new_url = re.sub(param_regix, new_value, target.url)
            http_flow.request.url = new_url

        except Exception as e:
            print(f"Error editing url param: {e}")

        return ActionResult.continue_()
    
class RemoveUrlParam(Action):
    name: str = "remove_url_param"
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        param_regix = self.params.get("param_regix")
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response

        try:
            new_url = re.sub(param_regix, "", target.url)
            target.url = new_url

        except Exception as e:
            print(f"Error removing url param: {e}")

        return ActionResult.continue_()
    
    
class ApplyAPGEncyption(Action):
    name: str = "apply_apg_encryption"

    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        c = ctx.data.get("c")
        v = ctx.data.get("v")
        m = ctx.data.get("m")
        y = ctx.data.get("y")
        pct = ctx.data.get("pct")
        n = ctx.data.get("n")
        e = ctx.data.get("e")
        sessionId = ctx.data.get("sessionId")
        merchantId = ctx.data.get("merchantId")
        
        card_data = {
            "c": c,
            "v": v,
            "m": m,
            "y": y,
            "pct": pct 
            }
        
        public_key = {
            "n": n,
            "e": e 
            }

        extra = {
            "sessionId": sessionId,
            "merchantId": merchantId
        }

        payload = {
            "cardData": card_data,
            "publicKey":public_key,
            "extra": extra
            }
        
        token = AuthManager().getToken()
        client = ApiClient.GetInstance("http://127.0.0.1:8000", token)
        end_ppoints = ApiEndpoints(client)
        try:
            res = end_ppoints.apply_apg_encyption(payload)
            print(res)
            return_name = self.params.get("return_name")
            ctx.data[return_name] = res.data
            print("done")
        except Exception as e:
            print(f"Error applying apg encyption: {e}")

        return ActionResult.continue_()

class ApplyFunctionAction(Action):
    def execute(self, ctx: FlowContext, http_flow: HTTPFlow) -> ActionResult:
        client = ApiClient.GetInstance("http://127.0.0.1:8000", "feb3e627a588e58f81dfef7e986a5b8c1051ca93")
        end_ppoints = ApiEndpoints(client)
        func_name = self.params.get("function")
        func = getattr(end_ppoints, func_name)
        func(http_flow.request)
        return ActionResult.continue_()
        

ACTION_MAP = {
    "detect": DetectAction,
    "edit_body": EditBodyAction,
    "edit_headers": EditHeadersAction,
    "reject": RejectAction,
    "redirect": RedirectAction,
    "forward": ForwardAction,
    "remove_body_element": RemoveBodyElementAction,
    "change_body" : ChangeBodyAction,
    "extract_header" : ExtractHeaderVariableAction,
    "remove_header" : RemoveHeaderAction,
    "extract_body_element": ExtractBodyElementAction,
    "extract_query":ExtractQueryAction,
    "edit_query":EditQueryAction,
    "remove_query": RemoveQueryAction,
    "change_status_code": ChangeStatusCodeAction,
    "insertHeaderKey": InsertHeaderKey,
    "customDetect": CustomDetectAction,
    
    "editUrlParam" : EditUrlParam,
    "removeUrlParam": RemoveUrlParam,
    "extractURLParams": ExtractURlParam,

    "APGMastercard": ApplyAPGEncyption
# CybersourceFlexV2
}

