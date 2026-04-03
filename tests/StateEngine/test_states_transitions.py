# tests/StateEngine/test_state_transitions.py
import pytest
from mitmproxy.test.tflow import tflow
from mitmproxy.http import Response, Headers

from FlowEngine.FlowManager import BasicFlow, OptionalFlow, FixedFlow
from FlowEngine.StateEngine import FixedFlowRunningState, FlowRuntime, IdleState, SearchForBasicFlowState, BasicFlowRunningState, SearchForBasicOptionalFlowState, SearchForOptionalFlowState, SearchforFixedFlowState
from FlowEngine.Actions import Phase, Action
from FlowEngine.custom_types import FlowContext, StateResult

class MockAction(Action):
    def __init__(self, *, pass_check=True, phase=Phase.REQUEST, write_key=None, write_value=None):
        super().__init__(url_regex=".*", phase=phase)
        self.pass_check = pass_check
        self.executed = False
        self.write_key = write_key
        self.write_value = write_value

    def check(self, flow):
        return self.pass_check

    def execute(self, ctx: FlowContext, flow):
        self.executed = True
        if self.write_key is not None:
            ctx.set(self.write_key, self.write_value)
        return None

def make_request_flow():
    flow = tflow()
    flow.response = None
    return flow

def make_response_flow(status=200, body=b"ok"):
    flow = tflow()
    flow.response = Response.make(
        status_code=status,
        content=body,
        headers=Headers()
    )
    return flow


def test_idle_to_search_basic():
      """
      create runtime and go from idle to search for basic
      add flows to runtimes
      """
      runtime = FlowRuntime([], [], [])

      runtime.state = IdleState()
      result = runtime.step(make_request_flow())

      assert isinstance(runtime.state, SearchForBasicFlowState)
      assert runtime.active_flow is None
      assert result == StateResult.ProceedEvent

def test_search_basic_flow_found():
    action = MockAction(pass_check=True)
    basic = BasicFlow(actions=[action])
    runtime = FlowRuntime([basic], [], [])
    
    runtime.state = SearchForBasicFlowState()
    result = runtime.step(make_request_flow())

    assert runtime.active_flow is basic
    assert isinstance(runtime.state, BasicFlowRunningState)
    assert result == StateResult.ProceedRequest


def test_search_basic_flow_not_found_goes_optional():
    """
    create runtime and go from idle to search for basic
    """
    runtime = FlowRuntime([], [], [])
    runtime.state = SearchForBasicFlowState()
    result = runtime.step(make_request_flow())

    assert isinstance(runtime.state, SearchForOptionalFlowState)
    assert result == StateResult.ProceedEvent


def test_basic_flow_running_finishes():
    """
    create runtime and go from idle to search for basic
    """

    action = MockAction(pass_check=True)
    basic = BasicFlow(actions=[action])
    basic.context = FlowContext()
    runtime = FlowRuntime([basic], [], [])

    runtime.active_flow = basic
    runtime.state = BasicFlowRunningState()

    result = runtime.step(make_request_flow())

    assert isinstance(runtime.state, SearchForBasicOptionalFlowState)
    assert result == StateResult.ProceedRequest
    assert action.executed is True


def test_optional_flow_running_finishes():
    action = MockAction(pass_check=True)
    optional = OptionalFlow(actions=[action])
    optional.context = FlowContext()
    runtime = FlowRuntime([], [optional], [])
    from FlowEngine.StateEngine import OptionalFlowRunningState, SearchforFixedFlowState

    runtime.active_flow = optional
    runtime.state = OptionalFlowRunningState()

    result = runtime.step(make_request_flow())

    assert isinstance(runtime.state, SearchforFixedFlowState)
    assert result == StateResult.ProceedRequest
    assert action.executed is True

    
def test_fixed_flow_running_finishes():
    """
    create runtime and go from idle to search for basic, then fixed.
    so that fixed is active flow and running
    """
    action = MockAction(pass_check=True)
    fixed = FixedFlow(actions=[action, action])
    fixed.context = FlowContext()
    runtime = FlowRuntime([], [], [fixed])

    runtime.state = SearchforFixedFlowState()
    result = runtime.step(make_request_flow())

    assert isinstance(runtime.state, FixedFlowRunningState)
    assert runtime.active_flow is fixed

    # Run FixedFlowRunningState
    result2 = runtime.step(make_request_flow())
    assert isinstance(runtime.state, IdleState)
    assert result2 == StateResult.ProceedRequest
    assert action.executed is True
