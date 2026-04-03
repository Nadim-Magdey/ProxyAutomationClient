from abc import ABC, abstractmethod
from enum import Enum
from pdb import run
from shutil import ExecError
from mitmproxy.http import HTTPFlow
import re
from typing import Dict, Callable
from .ActionResult import ActionResult
from .utils import parse_url_queries, rebuild_url, url_to_regex

class RuleStatus(Enum):
    CONTINUE = 1
    INTERCEPTED = 2
    REJECTED = 3
    REDIRECTED = 4

class RuleTypes(Enum):
    Detect = 0
    Forward = 1
    Reject = 2
    Redirect = 3
    EditHeader = 4
    EditBody = 5
    ChangeBody = 6
    ExtractHeaderVariable = 7
    EditQuery = 8
    ExtractQuery = 9
    AddQuery = 10
    ExctractBodyElement = 11
    RemoveBodyElement = 12
    RemoveHeaderRule = 13
    RemoveQueryRule = 14

class Methods(str, Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"

class RulePhase(Enum):
    REQUEST = 0
    RESPONSE = 1

class Rule(ABC):
    def __init__(self, method: Methods, rule_phase: RulePhase, callback: Callable[[ActionResult, object], None],
                 url_regix: str, context):
        self.callback = callback
        self.rule_phase = rule_phase
        self.method = method
        self.url_regix = url_regix
        self.context = context

    def Check(self, flow: HTTPFlow) -> bool:
        class_name = self.__class__.__name__
        print(f"{class_name}, start processing")

        request = flow.request

        # Method check only for request phase
        if self.rule_phase == RulePhase.REQUEST:
            if request.method.upper() != self.method.value:
                print("failed checking method")
                return False

        # URL check
        regix_url = url_to_regex(self.url_regix)
        if re.search(regix_url, request.url) is None:
            print("failed checking url regex:", request.url)
            return False

        print("success checking")
        return self._specify_checks(flow)

    @abstractmethod
    def _specify_checks(self, flow: HTTPFlow) -> bool:
        pass

    @abstractmethod
    def Execute(self, flow: HTTPFlow) -> RuleStatus:
        pass


class DetectRule(Rule):
    def _specify_checks(self, flow):
        return True

    def Execute(self, flow) -> RuleStatus:
        actionResult = ActionResult(success=True, message="Detected")
        data = {
            "url": flow.request.pretty_url,
            "method": flow.request.method
        }
        actionResult.setData(data)

        self.callback(actionResult, self.context)
        return RuleStatus.INTERCEPTED


class EditHeaders(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context, values: Dict):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.values = values

    def _specify_checks(self, flow):
        return True

    def Execute(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
        if target and hasattr(target, "headers"):
            for k, v in self.values.items():
                target.headers[k] = v
        action_result = ActionResult(success=True, message="Headers edited")
        action_result.setData({"headers": dict(target.headers)})
        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE

class RemoveHeaderRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context, header_key):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.header_key = header_key
        
    def _specify_checks(self, flow):
        return True
    
    def Execute(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
        if target and hasattr(target, "headers"):
            if self.header_key in target.headers:
                del target.headers[self.header_key]
        action_result = ActionResult(success=True, message="Header removed")
        action_result.setData({"removed_header": self.header_key})
        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE
    
    
class ChangeBody(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context, content):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.content = content

    def _specify_checks(self, flow):
        return True

    def Execute(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
        if target is not None and hasattr(target, "content"):
            if not target.content:
                raise Exception("target don't have content!!")
            target.content = self.content

        action_result = ActionResult(success=True, message="Body changed")

        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE

class EditBody(Rule):
    def __init__(self, method, rule_phase, callback, url_regix,context, element_regix, new_value):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.new_value = new_value
        self.element_regix = element_regix

    def _specify_checks(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
        body_text = target.get_text() if target else ""
        return bool(re.search(self.element_regix, body_text))

    def Execute(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
        if target is not None:
            
            body = target.get_text()
            new_body = re.sub(self.element_regix, self.new_value, body, count=1)
            target.set_text(new_body)
            action_result = ActionResult(success=True, message="Body element replaced")
            action_result.setData({"new_body": new_body})

            self.callback(action_result, self.context)

        return RuleStatus.CONTINUE
        
class ExtractBodyElementRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context, element_regix, return_name):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.element_regix = element_regix
        self.return_name = return_name

    def Execute(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response

        if target.content is None:
            raise Exception("target doesn;t have body")
        
        content = target.content.decode('utf-8', errors='ignore')
        print("element regix",self.element_regix)
        element = re.search(self.element_regix, content)
        print(f"element is {element}")

        action_result = ActionResult(True,"success")
        action_result.setData({
            "element_name":self.return_name,
            "element_value":element
        })
        
        self.callback(action_result,self.context)
        
        return RuleStatus.CONTINUE

    def _specify_checks(self, flow):
        return True

class RemoveBodyElementRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context, element_regix):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.element_regix = element_regix
    
    def Execute(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
        if target is not None:
            body = target.get_text()

            new_body, count = re.subn(self.element_regix, "", body, count=1, flags=re.DOTALL)
            
            if count == 0:
                print("warning: no match found for element_regix")
            
            target.set_text(new_body)
            
            action_result = ActionResult(success=True, message="body element replaced")
            action_result.setData({"new_body": new_body})
            self.callback(action_result, self.context)
            
        return RuleStatus.CONTINUE

    # def Execute(self, flow):
    #     target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
    #     if target is not None:
    #         body = target.get_text()
    #         new_body = re.sub(self.element_regix, "", body, count=1)
    #         target.set_text(new_body)
    #         action_result = ActionResult(success=True, message="Body element replaced")
    #         action_result.setData({"new_body": new_body})
    #         self.callback(action_result, self.context)

    #     return RuleStatus.CONTINUE
        
    def _specify_checks(self, flow):
        return True
    
class Reject(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context):
        super().__init__(method, rule_phase, callback, url_regix, context)

    def _specify_checks(self, flow):
        return True

    def Execute(self, flow):
        if self.rule_phase == RulePhase.REQUEST:
            # Kill the request upstream
            flow.kill()
            action_result = ActionResult(success=True, message="Request killed")
        elif self.rule_phase == RulePhase.RESPONSE:
            # Block the response: send empty content and 403
            if flow.response:
                flow.response.status_code = 403
                flow.response.content = b"Blocked by proxy"
            action_result = ActionResult(success=True, message="Response blocked")
        
        self.callback(action_result, self.context)
        return RuleStatus.REJECTED

class Redirect(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context, distination: str):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.distination = distination

    def _specify_checks(self, flow):
        return True

    def Execute(self, flow):
        target = flow.request if self.rule_phase == RulePhase.REQUEST else flow.response
        if target is not None:
            target.url = self.distination
        action_result = ActionResult(success=True, message="Redirect applied")
        action_result.setData({"distination": self.distination})
        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE

class Forward(Rule):
    def _specify_checks(self, flow):
        return True

    def Execute(self, flow):
        action_result = ActionResult(success=True, message="Forwarded")
        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE

class ExtractHeaderVariable(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context, header_key: str):
        super().__init__(method, rule_phase, callback, url_regix, context)
        self.header_key = header_key

    def _specify_checks(self, flow):
        return True

    def Execute(self, flow):
        # Decide which headers to read
        if self.rule_phase == RulePhase.REQUEST:
            target_headers = flow.request.headers
        elif self.rule_phase == RulePhase.RESPONSE:
            if not flow.response:
                print("No response yet, skipping ExtractHeaderVariable")
                return RuleStatus.CONTINUE
            target_headers = flow.response.headers

        header_value = target_headers.get(self.header_key)
        action_result = ActionResult(success=True, message="Header extracted")
        action_result.setData({"header_key": self.header_key, "header_value": header_value})

        print(f"ExtractHeaderVariable: calling callback, key={self.header_key}, value={header_value}")
        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE

class EditQueryRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context
                    , values: Dict):
            super().__init__(method, rule_phase, callback, url_regix, context)
            self.values = values

    def Execute(self, flow):
        url = flow.request.pretty_url if self.rule_phase == RulePhase.REQUEST else None
        if not url:
            return ActionResult(False)

        parsed, queries = parse_url_queries(url)

        for k, v in self.values.items():
            if k in queries:
                queries[k] = v

        new_url = rebuild_url(parsed, queries)
        flow.request.url = new_url

        return ActionResult(True, {"url": new_url})

class AddQueryRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context
                    , values: Dict):
            super().__init__(method, rule_phase, callback, url_regix, context)
            self.values = values

    def Execute(self, flow):
        url = flow.request.pretty_url if self.rule_phase == RulePhase.REQUEST else None
        if not url:
            return ActionResult(False)

        parsed, queries = parse_url_queries(url)

        for k, v in self.values.items():
            queries[k] = v 

        new_url = rebuild_url(parsed, queries)
        flow.request.url = new_url
        action_result = re.ActionResult(True, "sucess")
        action_result.setData({"new_url": new_url})

        self.callback(action_result,self.context)

        return ActionResult(True, {"url": new_url})

    def _specify_checks(self, flow):
        return True
    
class ExtractQueryRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context
                    , query_key: str):
            super().__init__(method, rule_phase, callback, url_regix, context)
            self.query_key = query_key

    def Execute(self, flow):
        url = flow.request.pretty_url if self.rule_phase == RulePhase.REQUEST else None
        if not url:
            return ActionResult(False)

        parsed, queries = parse_url_queries(url)

        key = self.query_key
        if key not in queries:
            return ActionResult(False)

        action_result = ActionResult(True,"success")
        action_result.setData({
            "query_key": key,
            "query_value": queries[key]
        })

        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE
    
    def _specify_checks(self, flow):
        return True
    
class RemoveQueryRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context
                    , query_key: str):
            super().__init__(method, rule_phase, callback, url_regix, context)
            self.query_key = query_key
    
    def Execute(self, flow):
        url = flow.request.pretty_url if self.phase == RulePhase.REQUEST else None
        if not url:
            return ActionResult(False)

        parsed, queries = parse_url_queries(url)

        key = self.query_key
        if key in queries:
            del queries[key]

        new_url = rebuild_url(parsed, queries)
        flow.request.url = new_url

        action_result = ActionResult(True, {
            "new_url": new_url
        })

        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE

    def _specify_checks(self, flow):
        return True

class EditQueryRule(Rule):
    def __init__(self, method, rule_phase, callback, url_regix, context
                    , query_key: str, new_value: str):
            super().__init__(method, rule_phase, callback, url_regix, context)
            self.query_key = query_key
            self.new_value = new_value
    def Execute(self, flow):
        url = flow.request.pretty_url if self.phase == RulePhase.REQUEST else None
        if not url:
            return ActionResult(False)

        parsed, queries = parse_url_queries(url)

        key = self.query_key
        if key not in queries:
            return ActionResult(False)

        queries[key] = self.new_value

        new_url = rebuild_url(parsed, queries)
        flow.request.url = new_url

        action_result = ActionResult(True, {
            "new_url": new_url
        })

        self.callback(action_result, self.context)
        return RuleStatus.CONTINUE
    
    def _specify_checks(self, flow):
        return True
