# tests/StateEngine/test_state_transitions.py
import pytest
from mitmproxy.test.tflow import tflow
from mitmproxy.http import Response, Headers

from FlowEngine.FlowManager import BasicFlow, OptionalFlow, FixedFlow, FlowManager
from FlowEngine.StateEngine import FixedFlowRunningState, FlowState, IdleState, SearchForBasicFlowState, BasicFlowRunningState, SearchForBasicOptionalFlowState, SearchForOptionalFlowState, SearchforFixedFlowState
from FlowEngine.Actions import Phase, Action
from FlowEngine.custom_types import FlowContext, StateResult
import re
"""
tests to make sure that the state engine works
it include providing requests to FlowManager.handle_request()
...........................................................

say we have basic flow b1 with actions (a1, a2, a3,..., an)
with 2 optional flows
o1 with actions (o1, o2, o3,..., on)
and o2 with actions (o1, o2, o3,..., on)

and basic flow b2 with actions (b1, b2, b3,..., bn)
with optional flows o1 and o2 

and have independant optional flows o3 and o4

and fixed flows f1, f2

now we want to design test scenarious :
given that we have 8  list of request/response http_flows
so that each list represents an http flow sequence
........................................................
scenarios deveided into groups:
1)strait scenarious: where comming http_flows always match next action 
2)non strait scenarious: where comming http_flows may or may not match next action
3)optional inturrupted scenarios, where basic flow finish then identical optional or fixed flow is executed

"""

class MockAction(Action):
    """
    mock action for testing, with check and execute that pass or fail
    """
    name = "mock_action"

    def __init__(
        self,
        *,
        phase=Phase.REQUEST,
        pass_check=True,
        write_key=None,
        write_value=None,
        url_regix = None
    ):
        # url_regex irrelevant in flow tests
        super().__init__(url_regex=".*", phase=phase)
        self.pass_check = pass_check
        self.write_key = write_key
        self.write_value = write_value
        self.executed = False
        self.url_regex = url_regix
    def check(self, http_flow):

        """
        check phase  and method
        finally return pass_check
        """
        if self.phase == Phase.REQUEST and http_flow.response is not None:
            print("no response")
            return False
        if self.phase == Phase.RESPONSE and http_flow.response is None:
            print("no response")
            return False
        # check url
        target = http_flow.request if self.phase == Phase.REQUEST else http_flow.response
        
        if not re.match(self.url_regex, target.url):
            print(f"{self.name} does not match URL {target.url}")
            return False
        
        return self.pass_check
    
    def execute(self, ctx, http_flow):
        """
        simulate execution, set executed to True and insert key/value 
        to context
        """
        self.executed = True
        if self.write_key:
            ctx.set(self.write_key, self.write_value)

def make_request_flow(url="http://address:22/path"):
    """
    create a request flow
    """
    flow = tflow()
    flow.request.url = url
    flow.response = None
    return flow

def make_response_flow(url="http://address:22/path", status=200, body=b"ok"):
    """
    create a response flow with a request URL, status and body
    """

    flow = tflow()
    # give request a URL so detector works
    flow.request.url = url
    # give a response (for response-phase actions)
    flow.response = Response.make(
        status_code=status,
        content=body,
        headers=Headers() 
              )
    flow.response.url = url
    return flow


def test_basic_flow_executes_untill_finish():
    http_flows = [
        make_request_flow(url="http://address:22/b1"),
        make_response_flow(url="http://address:22/b2", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b3"),
        make_response_flow(url="http://address:22/b4", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/b5"),
        make_response_flow(url="http://address:22/b6", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b7"),
        make_response_flow(url="http://address:22/b8", status=200, body=b"ok"),
    ]
    actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b4"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b5"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b6"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b7"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b8"),
    ]

    flow = BasicFlow(actions=actions)
    flow_manager = FlowManager()
    flow_manager.add_basic_flow(flow)
    flow_manager.InitiateRunTime()

    for http_flow in http_flows:
        print(f"feed http flow url {http_flow.request.url}")
        flow_manager.handle_request(http_flow)

    assert all([action.executed for action in actions]) 

def test_basic_flow_inturrputed_by_noise_request():
    """
    we have r1,r2,r4...,rO,....rn
    where rO not related to flow
    """
    http_flows = [
        make_request_flow(url="http://address:22/b1"),
        make_response_flow(url="http://address:22/b2", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b3"),
        make_response_flow(url="http://address:22/b4", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/b5"),
        make_response_flow(url="http://address:22/b6", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b7"),
        make_response_flow(url="http://address:22/b8", status=200, body=b"ok"),
    ]
    
    
    actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b4"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b5"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b6"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b7"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b8"),
    ]
    flow = BasicFlow(actions=actions)
    flow_manager = FlowManager()
    flow_manager.add_basic_flow(flow)
    flow_manager.InitiateRunTime()

    for i,http_flow in enumerate(http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    assert actions[0].executed
    assert actions[1].executed
    assert actions[2].executed
    assert actions[3].executed
    assert actions[4].executed
    assert actions[5].executed 
    assert actions[6].executed
    assert actions[7].executed


def test_basic_flow_followed_by_inner_optional_flow():
    """
    we have first sequence r1,...,rn  and then optional sequence rO1,...,rOn
    """
    basic_http_flows = [
        make_request_flow(url="http://address:22/b1"),
        make_response_flow(url="http://address:22/b2", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b3"),
        make_response_flow(url="http://address:22/b4", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/b5"),
        make_response_flow(url="http://address:22/b6", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b7"),
        make_response_flow(url="http://address:22/b8", status=200, body=b"ok"),
    ]
    
    optional_http_flows = [
        make_request_flow(url="http://address:22/bO1"),
        make_response_flow(url="http://address:22/bO2", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/bO3"),
        make_response_flow(url="http://address:22/bO4", status=200, body=b"ok"),
                           ]
    
    basic_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b4"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b5"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b6"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b7"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b8"),
    ]

    optional_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/bO1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/bO2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/bO3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/bO4"),
    ]
    optional_flow = OptionalFlow(actions=optional_actions)

    basic_flow = BasicFlow(actions=basic_actions, optional_flows=[optional_flow])

    flow_manager = FlowManager()
    flow_manager.add_basic_flow(basic_flow)
    flow_manager.InitiateRunTime()
    # feed basic http_fows
    for i,http_flow in enumerate(basic_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    # feed optional http_fows
    for i,http_flow in enumerate(optional_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    assert all([action.executed for action in basic_actions]) 

    assert all([action.executed for action in optional_actions])

def test_basic_its_optionl_then_fixed():
    """
    we have first sequence r1,...,rn  and then optional sequence rO1,...,rOn
    and then fixed sequence rF1,...,rFn

    """
    basic_http_flows = [
        make_request_flow(url="http://address:22/b1"),
        make_response_flow(url="http://address:22/b2", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b3"),
        make_response_flow(url="http://address:22/b4", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/b5"),
        make_response_flow(url="http://address:22/b6", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b7"),
        make_response_flow(url="http://address:22/b8", status=200, body=b"ok"),
    ]

    optional_http_flows = [
        make_request_flow(url="http://address:22/bO1"),
        make_response_flow(url="http://address:22/bO2", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/bO3"),
        make_response_flow(url="http://address:22/bO4", status=200, body=b"ok"),
    ]

    fixed_http_flows = [
        make_request_flow(url="http://address:22/f1"),
        make_response_flow(url="http://address:22/f2", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/f3"),
        make_response_flow(url="http://address:22/f4", status=200, body=b"ok"),
        ]

    basic_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b4"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b5"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b6"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b7"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b8"),
    ]

    optional_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/bO1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/bO2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/bO3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/bO4"),
    ]

    fixed_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/f1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/f2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/f3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/f4"),
    ]

    optional_flow = OptionalFlow(actions=optional_actions)
    fixed_flow = FixedFlow(actions=fixed_actions)

    basic_flow = BasicFlow(actions=basic_actions, optional_flows=[optional_flow])

    flow_manager: FlowManager = FlowManager()
    flow_manager.add_basic_flow(basic_flow)
    flow_manager.add_fixed_flow(fixed_flow)
    flow_manager.InitiateRunTime()

    # feed basic http_fows
    for i,http_flow in enumerate(basic_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    # feed optional http_fows
    for i,http_flow in enumerate(optional_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    # feed fixed http_fows
    for i,http_flow in enumerate(fixed_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    assert all([action.executed for action in basic_actions]) 

    assert all([action.executed for action in optional_actions])

    assert all([action.executed for action in fixed_actions])


def test_basic_its_optionl_then_indpendent_optionl_then_fixed():
    feedback = []

    print("*"*100)
    """
    we have first sequence r1,...,rn  and then  it's optional sequence rO1,...,rOn
    and then independant optional sequence rO1,...,rOn
    then fixed sequence rF1,...,rFn
    """
    basic_http_flows = [
        make_request_flow(url="http://address:22/b1"),
        make_response_flow(url="http://address:22/b2", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b3"),
        make_response_flow(url="http://address:22/b4", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/b5"),
        make_response_flow(url="http://address:22/b6", status=200, body=b"ok"),
        make_request_flow(url="http://address:22/b7"),
        make_response_flow(url="http://address:22/b8", status=200, body=b"ok"),
    ]

    optional_http_flows = [
        make_request_flow(url="http://address:22/bO1"),
        make_response_flow(url="http://address:22/bO2", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/bO3"),
        make_response_flow(url="http://address:22/bO4", status=200, body=b"ok"),
    ]

    independent_optional_http_flows = [
        make_request_flow(url="http://address:22/O1"),
        make_response_flow(url="http://address:22/O2", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), # noise
        make_request_flow(url="http://address:22/O3"),
        make_response_flow(url="http://address:22/O4", status=200, body=b"ok"),
    ]


    fixed_http_flows = [
        make_request_flow(url="http://address:22/f1"),
        make_response_flow(url="http://address:22/f2", status=200, body=b"ok"),
        make_response_flow(url="http://address:22/noise"), #noise
        make_request_flow(url="http://address:22/f3"),
        make_response_flow(url="http://address:22/f4", status=200, body=b"ok"),
        ]

    basic_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b4"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b5"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b6"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b7"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b8"),
    ]

    optional_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/bO1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/bO2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/bO3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/bO4"),
        ]

    independent_optional_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/O1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/O2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/O3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/O4"),
    ]

    fixed_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/f1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/f2"),
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/f3"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/f4"),
    ]

    optional_flow = OptionalFlow(actions=optional_actions)
    independent_optional_flow = OptionalFlow(actions=independent_optional_actions)
    fixed_flow = FixedFlow(actions=fixed_actions)

    basic_flow = BasicFlow(actions=basic_actions, optional_flows=[optional_flow])

    flow_manager: FlowManager = FlowManager()
    flow_manager.add_basic_flow(basic_flow)
    flow_manager.add_optional_flow(independent_optional_flow)
    flow_manager.add_fixed_flow(fixed_flow)
    flow_manager.InitiateRunTime()

    # feed basic http_fows
    for i,http_flow in enumerate(basic_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    
    # feed optional http_fows
    for i,http_flow in enumerate(optional_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    for i,http_flow in enumerate(independent_optional_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    # feed fixed http_fows
    for i,http_flow in enumerate(fixed_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    assert all([action.executed for action in basic_actions]) 

    assert all([action.executed for action in optional_actions])

    assert all([action.executed for action in independent_optional_actions])

    assert all([action.executed for action in fixed_actions])



def test_on_basic_detection_event_is_called():
    """
    make sure on_basic_detection_event is called
    """

    basic_http_flows = [
        make_request_flow(url="http://address:22/b1"),
        make_response_flow(url="http://address:22/b2", status=200, body=b"ok"),
    ]

    basic_actions = [
        MockAction(phase=Phase.REQUEST, pass_check=True, url_regix=r"http://address:22/b1"),
        MockAction(phase=Phase.RESPONSE, pass_check=True, url_regix=r"http://address:22/b2"),
    ]

    basic_flow = BasicFlow(actions=basic_actions)

    flow_manager: FlowManager = FlowManager()
    flow_manager.add_basic_flow(basic_flow)
    flow_manager.InitiateRunTime()

    # feed basic http_fows
    for i,http_flow in enumerate(basic_http_flows):
        print(f"feed http_flow of index {i}")
        flow_manager.handle_request(http_flow)

    assert all([action.executed for action in basic_actions])

    