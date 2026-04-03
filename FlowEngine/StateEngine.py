from abc import ABC, abstractmethod
from os import access
import re
import threading
from tests.conftest import context
from.custom_types import Phase, StateResult, EngineEvent, StepResult, Events
class FlowRuntime:
    """
    Singleton Runtime for ONE mitmproxy request/response cycle
    Holds:
      - active flow
      - active shared context
      - current state
    """
    
    instance = None
    def __init__(self, basic_flows, optional_flows, fixed_flows):
        self.basic_flows  = basic_flows
        self.optional_flows  = optional_flows 
        self.fixed_flows  = fixed_flows
        
        self.active_flows = None          # Basic or Optional flow
        
        self.state: FlowState = IdleState()
        
        print("FlowRuntime created")
        self.flow_manager = None
        self.pause_event = threading.Event()
        self.pause_event.set()  # initially not paused
        self.collected_inputs = None
        
    def step(self, http_flow):
        """Execute one state step"""
        try:
            result = self.state.handle(self, http_flow)
            return result
        except Exception as e:
            print(f"Error in state {self.state.__class__.__name__}: {e}")
            return   StateResult.ProceedEvent

    def getInstance(basic_flows, optional_flows, fixed_flows):
        
        if FlowRuntime.instance is None:
            FlowRuntime.instance = FlowRuntime(basic_flows, optional_flows, fixed_flows)
        return FlowRuntime.instance
        
class FlowState(ABC):
    @abstractmethod
    def handle(self, runtime: FlowRuntime, http_flow):
        pass
        
class IdleState(FlowState):
    """
    Initial state.
    Waits for a new request/response to process.
    Transitions to SearchForBasicFlowState.
    """

    def handle(self, runtime: FlowRuntime, http_flow):
        print("IdleState handle" )
        #clear active flow and context
        runtime.active_flow = None
        runtime.state = SearchForBasicFlowState()

        return StepResult(StateResult.ProceedEvent, None)
    
class SearchForBasicFlowState(FlowState):
    """
    Search for basic flow that matches the current request and phase.
    if found, set it as the active flow and transition to BasicFlowRunningState
    and return StateResult.ProceedRequest

    if none found, transiion to SearchForOptionalFlowState
    with return StateResult.ProceedEvent

    """
    
    def handle(self, runtime: FlowRuntime, http_flow):
        # print("Current State: Search for basic Flow ")
        basic_flows = runtime.basic_flows

        # print(f"basic flows are ",basic_flows)
        for basic  in runtime.basic_flows:
            try:
                if basic.matches(http_flow):
                    
                    print(f"Found matching basic flow {basic.name}")
                    print("next action",basic.next_action().name)
                    # Found matching basic flow
                    basic.reset()
                    # log action if needed
                    referrer = http_flow.request.headers.get("Referer")
                    origin = http_flow.request.headers.get("Origin")
                    info = f"referrer: {referrer}, origin: {origin}"
                    res = basic.next_action().log_if_needed(basic.name, 
                                                            "BASIC_DETECTED", 
                                                            info)
                    
                    basic.reset()
                    
                    # ececute 
                    basic.next_action().execute(basic.context, http_flow)
                    runtime.active_flow = basic

                    # wait untill inputs filled 
                    # runtime.flow_manager.basic_detected.emit(basic)
                    # runtime.flow_manager.on_basic_detected(basic)
                    
                    # runtime.pause_event.clear()
                    # runtime.pause_event.wait()
                    # # save inputs values to context
                    # print(f"rcieved inputs {runtime.collected_inputs}")
                    
                    runtime.state = BasicFlowRunningState()

                    return StepResult( StateResult.ProceedRequest,
                            EngineEvent(Events.BASIC_DETECTED, basic) )
                
            except Exception as e:
                print(f"Error in Search for basic flow {e}")

        runtime.state = SearchForOptionalFlowState()
        # return StateResult.ProceedEvent
        return StepResult(StateResult.ProceedEvent, None)

#basic Flows classes
class BasicFlowRunningState(FlowState):
    """
    iterate over the actions of the active basic flow
    and execute them untill done or waiting for next request/response

    in case finish transition to SearchForOptionalFlowState
      with return StateResult.ProceedRequest

    in case still actions left or waiting for next request/response
      return StateResult.ProceedRequest
      
    """
    
    def handle(self, runtime: FlowRuntime, http_flow):
        # print(f"Current State: BasicFlowRunningState")
        flow = runtime.active_flow        
        ctx = flow.context
        # continue executing from the next action untill done or waiting for next request/response

        while flow.has_next() and flow.check_next(http_flow):
            
            action = flow.next_action()
            action.log_if_needed(flow.name, 
                                "ACTION_EXECUTED", 
                                f"action {action.name} executed")
            action.execute(ctx, http_flow)

        # Check if finished
        if flow.is_finished():
            flow.log(
                flow.name, 
                "FLOW_FINISHED", 
                f"flow {flow.name} finished"
            )
            flow.reset()



            print("proceed request")
            runtime.state = SearchForBasicOptionalFlowState()
            return StepResult(StateResult.ProceedRequest, 
                              EngineEvent(Events.BASIC_FINISHED, flow))

        # Still actions left or waiting for next request/response
        return StepResult(StateResult.ProceedRequest, None)

class BasicOptionalFlowRunningState(FlowState):
    """
        iterate over the actions of the active basic flow
        and execute them untill done or waiting for next request/response

        in case finish transition to SearchForFixedFlowState
          with return StateResult.Procee
          
        in case still actions left or waiting for next request/response
          return StateResult.ProceedRequest
    """
    
    def handle(self, runtime: FlowRuntime, http_flow):
        flow = runtime.active_flow
        ctx = flow.context
        
        # continue executing from the next action untill done or waiting for next request/response
        while flow.has_next() and flow.check_next(http_flow):
            action = flow.next_action()
            action.log_if_needed(flow.name, 
                                "ACTION_EXECUTED", 
                                f"action {action.name} executed")
            action.execute(ctx, http_flow)
            
        # Check if finished
        if flow.is_finished():
            flow.log(
                flow.name, 
                "OPTIONAL_FLOW_FINISHED", 
                f"flow {flow.name} finished"
            )
            flow.reset()
            runtime.state = SearchforFixedFlowState()
            # return StateResult.ProceedRequest
            return StepResult(StateResult.ProceedRequest, None)

        # Still actions left or waiting for next request/response
        # return StateResult.ProceedRequest
        return StepResult(StateResult.ProceedRequest, None)
    
class SearchForBasicOptionalFlowState(FlowState):
    """
    Search for optional flow that matches the current request and phase.
    If found, transition to BasicOptionalFlowRunningState.
    with return StateResult.ProceedRequest

    else :
        transition to SearchForFixedFlowState with 
        return StateResult.ProceedEvent
    """

    def handle(self, runtime: FlowRuntime, http_flow):
        basic = runtime.active_flow
        ctx = basic.context
        
        for opt in basic.optional_flows:
            
            if opt.matches(http_flow):
                opt.reset()
                runtime.active_flow = opt
                referrer = http_flow.request.headers.get("Referer")
                origin = http_flow.request.headers.get("Origin")
                info = f"referrer: {referrer}, origin: {origin}"
                opt.log(
                    opt.name, 
                    "OPTIONAL_FLOW_DETECTED_AFTER_BASIC_FLOW", 
                    info
                )
                opt.next_action().execute(ctx, http_flow)

                runtime.state = BasicOptionalFlowRunningState()
                # return StateResult.ProceedRequest
                return StepResult(StateResult.ProceedRequest, None)

        runtime.state = SearchForOptionalFlowState()
        # return StateResult.ProceedEvent
        return StepResult(StateResult.ProceedEvent, None)
    
#optional Flows classes
class SearchForOptionalFlowState(FlowState):
    """
    Search for optional flow that matches the current request and phase.
    If found, transition to OptionalFlowRunningState.
    with return StateResult.ProceedRequest
    else 
        transition to SearchForFixedFlowState with 
        return StateResult.ProceedRequest
    """
    
    def handle(self, runtime: FlowRuntime, http_flow):

        for opt in runtime.optional_flows:
            if opt.matches(http_flow):
                referrer = http_flow.request.headers.get("Referer")
                origin = http_flow.request.headers.get("Origin")
                info = f"referrer: {referrer}, origin: {origin}"
                opt.log(
                    opt.name, 
                    "Optional_FLOW_DETECTED", 
                    info
                )

                runtime.active_flow = opt
                opt.next_action().execute(opt.context, http_flow)
                opt.reset()
                runtime.state = OptionalFlowRunningState()
                # return StateResult.ProceedRequest
                return StepResult(StateResult.ProceedEvent, None)

        # No matching optional flow found
        runtime.state = SearchforFixedFlowState()
        # return StateResult.ProceedEvent
        return StepResult(StateResult.ProceedEvent, None)

class OptionalFlowRunningState(FlowState):
    """
    Run the active optional flow with shared context.
    Transition to PassThroughState when optional flow finishes.
    """

    def handle(self, runtime: FlowRuntime, http_flow):
        flow = runtime.active_flow
        ctx = flow.context
        # continue executing from the next action untill done or waiting for next request/response
        while flow.has_next() and flow.check_next(http_flow):
            action = flow.next_action()
            action.log_if_needed(flow.name, 
                                "ACTION_EXECUTED", 
                                f"action {action.name} executed")
            try:
                action.execute(ctx, http_flow)
                print("action executed")
            except Exception as e:
                print(f"Error in optional running: {e}")

        # Check if finished
        if flow.is_finished():
            flow.log(
                flow.name, 
                "OPTIONAL_FLOW_FINISHED", 
                f"flow {flow.name} finished"
            )
            flow.reset()
            runtime.state = SearchforFixedFlowState()
            # return StateResult.ProceedRequest
            return StepResult(StateResult.ProceedRequest, None)
        
        # Still actions left or waiting for next request/response
        # return StateResult.ProceedRequest
        return StepResult(StateResult.ProceedRequest, None)
        
#fixed Flows classes
class SearchforFixedFlowState(FlowState):
    """
    Search for fixed flow to run.
    If found, set it as the active flow and transition to FixedFlowState.
    If none found, transition to PassThroughState.
    """
    
    """
    Note : check reset() validity here in potential edge cases 
    """
    def handle(self, runtime: FlowRuntime, http_flow):
        flows = runtime.fixed_flows
        
        for flow in flows:
            try:
                if flow.matches(http_flow):
                    referrer = http_flow.request.headers.get("Referer")
                    origin = http_flow.request.headers.get("Origin")
                    info = f"referrer: {referrer}, origin: {origin}"
                    flow.log(
                        flow.name, 
                        "FIXED_FLOW_DETECTED", 
                        info
                )
                    flow.next_action().execute(flow.context, http_flow)
                    # flow.reset()
                    runtime.active_flow = flow
                    runtime.state = FixedFlowRunningState()
                    # return StateResult.ProceedEvent
                    return StepResult(StateResult.ProceedEvent, None)
            except Exception as e:
                print(f"Error in fixed flow search: {e}")
        # No matching fixed flow found
        runtime.state = IdleState()
        # return StateResult.ProceedRequest
        return StepResult(StateResult.ProceedRequest, None)

class FixedFlowRunningState(FlowState):
    """
    Run the active basic or optional flow with shared context.
    Transition to OptionalState when basic flow finishes.
    Transition to PassThroughState when optional flow finishes.
    """
    
    def handle(self, runtime: FlowRuntime, http_flow):
        
        flow = runtime.active_flow
        ctx = flow.context
        # continue executing from the next action untill done or waiting for next request/response  
        try:
            while flow.has_next() and flow.check_next(http_flow):

                action = flow.next_action()
                action.log_if_needed(flow.name, 
                                    "ACTION_EXECUTED", 
                                    f"action {action.name} executed")
                action.execute(ctx, http_flow)
                print("action executed")
            # Check if finished 
            if flow.is_finished():
                flow.log(
                    flow.name, 
                    "FIXED_FLOW_FINISHED", 
                    f"flow {flow.name} finished"
                )
                flow.reset()

                if flow.has_notification():
                    success = flow.apply_condition(http_flow)

                    flow.notify_server(flow.context,success)

                    runtime.state = IdleState()

                    return StepResult(StateResult.ProceedRequest, 
                                        EngineEvent(Events.FIXED_FINISHED
                                                    , {
                                                        "success": success,
                                                        "flow": flow,
                                                        "context": flow.context
                                                    }))
        except Exception as e:
            print(f"Error in fixed running: {e}")
        # Still actions left or waiting for next request/response
        return StepResult(StateResult.ProceedRequest, None)

class CyvceFinishedState(FlowState): 
    """
    Dead State for Cycle
    """
    def handle(self, runtime: FlowRuntime, http_flow):
        pass
