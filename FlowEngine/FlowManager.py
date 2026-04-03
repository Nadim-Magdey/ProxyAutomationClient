from typing import List, Dict, Any
from Api.Client import ApiClient
from Api.data.AuthEngine.AuthManager import AuthManager
from Api.end_ppoints import ApiEndpoints
from .Actions import Action, FlowContext
from mitmproxy.http import HTTPFlow
from .custom_types import EngineEvent, Events, FlowContext, StateResult, StepResult
from .StateEngine import FlowRuntime
from PyQt6.QtCore import pyqtSignal, QObject
import re 

class Flow:
    """Base flow abstraction"""
    def __init__(self, actions: List[Action], group = None,name="flow"):
        self.name = name
        self.actions = actions
        self._cursor = 0
        self.context: FlowContext | None = None  # each flow owns its context
        self.group = group

    def matches(self, flow_obj: HTTPFlow) -> bool:
        if not self.actions:
            return False

        detect = self.actions[0]
        return detect.check(flow_obj)

    def reset(self):
        self._cursor = 0
        
    def has_next(self) -> bool:
        return self._cursor < len(self.actions)
        
    def next_action(self):
        if not self.has_next():
            return None
        action = self.actions[self._cursor]
        self._cursor += 1
        return action
        
    def is_finished(self) -> bool:
        
        return self._cursor >= len(self.actions)

    def check_next(self, http_flow: HTTPFlow) -> bool:
        """check if next action is match or not"""
        if not self.has_next():
            return False
        
        next_action = self.actions[self._cursor]

        return next_action.check(http_flow)
    
    def log(self,service_name, logType, info):
        """
        logs the action if log  param is true
        """
        try:

            user_token = AuthManager.getInstance().getToken()

            api_client = ApiClient("http://127.0.0.1:8000", user_token)
            api_endpoints = ApiEndpoints(api_client)      
            return api_endpoints.log(
                service_name,
                    logType,
                    info 
            )
            
        except Exception as e:
            print(f"Error logging: ",e)

class OptionalFlow(Flow):
    """Optional flow inherits context from its parent basic flow"""
    def matches(self, flow_obj: HTTPFlow) -> bool:
        if not self.actions:
            return False
        detect = self.actions[0]
        return detect.check(flow_obj)

class BasicFlow(Flow):
    def __init__(
        self,
        actions: List[Action],
        optional_flows: List[OptionalFlow] | None = None,
        group = None,
        name="basic",
        inputs: Dict[str, Any] | None = None,
       
    ):
        super().__init__(actions, group, name)
        self.optional_flows = optional_flows or []
        self.inputs = inputs or {}

        self.prepare()
        
    def prepare(self):
        for opt in self.optional_flows:
            opt.context = self.context
    
    def matches(self, flow_obj: HTTPFlow) -> bool:
        if not self.actions:
            return False
        
        detect = self.actions[0]
        return  detect.check(flow_obj)


class FixedFlow(Flow):
    def __init__(self, actions,name,  notify_condition ,success_value,notify_variables, group):
        super().__init__(actions, name = name, group=group)

        self.notify_condition = notify_condition
        self.success_value = success_value
        self.notify_variables = notify_variables
    """Independent fixed flow with its own context"""
    def matches(self, flow_obj: HTTPFlow) -> bool:
        if not self.actions:
            return False
        detect = self.actions[0]
        return detect.check(flow_obj)


    def has_notification(self):
        """
        Check if flow has notification
        """
        return self.notify_condition and self.notify_variables
        
    def apply_condition(self, http_flow):
        """
        Check if condition is met or not, based on condition type, regex and success

        """

        condition_type = self.notify_condition.get("type")
        regex_pattern = self.notify_condition.get("regex")
        success_value = self.notify_condition.get("success")
        
        try:
            if condition_type == "body_regex":
                if not http_flow.response:
                    return False

                body = http_flow.response.get_text()

                match = re.search(regex_pattern, body)
                if not match:
                    return False

                # If success defined → check it
                if success_value:
                    return success_value in body

                return True

            elif condition_type == "query":
                query = http_flow.request.query
                query_string = str(query)

                if re.search(regex_pattern, query_string):
                    if success_value:
                        return success_value in query_string
                    return True

                return False

            elif condition_type == "headers":
                headers = str(http_flow.response.headers)

                if re.search(regex_pattern, headers):
                    if success_value:
                        return success_value in headers
                    return True

                return False
                
        except Exception as e:
            print("Condition error:", e)
            return False

        return False

    def notify_server(self, context, is_success):
        
        try:
            flow_name = self.name
            variables = self.notify_variables
            
            user_token = AuthManager.getInstance().getToken()
            
            api_client = ApiClient("http://127.0.0.1:8000", user_token)
            api_endpoints = ApiEndpoints(api_client)   
            
            return api_endpoints.notify(
                variables,
                context,
                is_success
            )
            
        except Exception as e:
            print(f"Error logging: ",e)

class FlowManager(QObject):
    basic_detected = pyqtSignal(object)
    basic_finished = pyqtSignal(object)
    notify_user = pyqtSignal(object)
    
    Instance = None

    def __init__(self):
        super().__init__()
        self.basic_flows: List[BasicFlow] = []
        self.fixed_flow: list[FixedFlow] = []
        self.optional_flows: List[OptionalFlow] = []
        
        # GUI callbacks
        self.on_basic_detected = lambda flow: None
        self.on_basic_finished = lambda flow: None

        self.on_user_notification = lambda flow, variables: None

    def InitiateRunTime(self):
        self.runtime = FlowRuntime(self.basic_flows, self.optional_flows, self.fixed_flow)
        self.runtime.flow_manager = self
        
    def add_basic_flow(self, flow: BasicFlow):
        self.basic_flows.extend(flow)

    def add_fixed_flow(self, flow: FixedFlow):
        self.fixed_flow.extend(flow)

    def add_optional_flow(self, flow: OptionalFlow):
        self.optional_flows.extend(flow)
        
    def handle_request(self, flow_obj: HTTPFlow):

        while True:
            result: StepResult = self.runtime.step(flow_obj)

            if result.event:
                self._handle_engine_event(result.event)
                
            if result.state == StateResult.ProceedEvent:
                continue

            if result.state == StateResult.ProceedRequest:
                break
            
            break

    def continue_running(self):
        self.runtime.pause_event.set()
    
    def pause_running(self):
        self.runtime.pause_event.wait()

    def provide_user_inputs(self, data):
        print("provide user inputs by flow manager")
        runtime = self.runtime
        flow = runtime.active_flow

        if flow:
            flow.context.update(data)

        runtime.pause_event.set()

    def _handle_engine_event(self, event: EngineEvent):

        
        if event.type == Events.BASIC_DETECTED:
            self.runtime.pause_event.clear()

            self.basic_detected.emit(event.payload)
            self.runtime.pause_event.wait()

        elif event.type == Events.BASIC_FINISHED:
            print(f"basic flow finished (by flow manager) {event.payload}")
            self.runtime.pause_event.clear()
            self.basic_finished.emit(event.payload)
            self.pause_running()

        elif event.type == Events.FIXED_FINISHED:
            """
                {
                    "success": success,
                    "flow": http_flow,
                    "context": flow.context
                }
            """
            try:
                print(f"fixed flow finished (by flow manager) {event.payload}")
                self.notify_user.emit(event.payload)
                self.pause_running()
            except Exception as e:
                print(f"Error logging: ",e)
                print(f"tarce back {e.__traceback__}")
    def GetInstance(event):
        
        if not FlowManager.Instance:
            FlowManager.Instance = FlowManager()
        return FlowManager.Instance

