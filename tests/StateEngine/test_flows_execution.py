"""
test flows execution without state machine
create BasicFlow, OptionalFlow, FixedFlow and feed them with MockActions

"""
from FlowEngine.FlowManager import BasicFlow,OptionalFlow,FixedFlow

from .mocks import MockAction, make_response_flow


from mitmproxy.test.tflow import tflow
from mitmproxy.http import Response, Headers
from FlowEngine.Actions import Action, Phase
from FlowEngine.custom_types import FlowContext


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
        headers=Headers(),
    )
    return flow

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
    ):
        # url_regex irrelevant in flow tests
        super().__init__(url_regex=".*", phase=phase)
        self.pass_check = pass_check
        self.write_key = write_key
        self.write_value = write_value
        self.executed = False

    def check(self, http_flow):
        """
        check phase, url regex and method
        finally return pass_check
        """
        if self.phase == Phase.REQUEST and http_flow.response is not None:
            return False
        if self.phase == Phase.RESPONSE and http_flow.response is None:
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


def run_flow(flow, http_flow):
    """
    Run a flow until completion
    """
    if flow.context is None:
        flow.context = FlowContext()

    while flow.has_next() and flow.check_next(http_flow):
        action = flow.next_action()
        action.execute(flow.context, http_flow)

    

def test_basic_flow_detects():
    action = MockAction(pass_check=True)
    flow = BasicFlow(actions=[action])

    http_flow = make_request_flow()
    assert flow.matches(http_flow) is True


def test_basic_flow_creates_own_context():
    action = MockAction(write_key="x", write_value=1)
    flow = BasicFlow(actions=[action])

    http_flow = make_request_flow()
    flow.context = FlowContext()

    run_flow(flow, http_flow)

    assert flow.context is not None
    assert flow.context.get("x") == 1


def test_basic_flow_context_is_unique_per_run():
    """
    Context should be unique per run
    """
    action = MockAction()
    flow = BasicFlow(actions=[action])

    http_flow = make_request_flow()

    flow.context = FlowContext()
    ctx1 = flow.context

    flow.reset()
    flow.context = FlowContext()
    ctx2 = flow.context

    assert ctx1 is not ctx2


def test_basic_flow_action_order():
    a1 = MockAction(write_key="step", write_value=1)
    a2 = MockAction(write_key="step", write_value=2)

    flow = BasicFlow(actions=[a1, a2])
    flow.context = FlowContext()
    
    run_flow(flow, make_request_flow())

    assert a1.executed is True
    assert a2.executed is True
    assert flow.context.get("step") == 2



def test_optional_flow_detects_standalone():
    action = MockAction(pass_check=True)
    flow = OptionalFlow(actions=[action])

    http_flow = make_request_flow()

    assert flow.matches(http_flow) is True


def test_optional_flow_standalone_owns_context():
    action = MockAction(write_key="opt", write_value=42)
    flow = OptionalFlow(actions=[action])

    http_flow = make_request_flow()
    flow.context = FlowContext()

    run_flow(flow, http_flow)

    assert flow.context.get("opt") == 42


def test_optional_flow_inherits_basic_context():
    """
    create basic flow and optional flow inside it with shared context
    test if optional flow automaticly use basic flow context
    """
    basic = BasicFlow(actions=[MockAction()])
    basic.context = FlowContext()

    optional = OptionalFlow(actions=[MockAction()])
    optional.context = basic.context

    run_flow(optional, make_request_flow())

    assert optional.context is basic.context
    

def test_optional_flow_writes_into_basic_context():
    """
    test wheather optional flow included inside basic ocntext and writes into it
    """

    basic = BasicFlow(actions=[MockAction()])
    basic.context = FlowContext()

    optional = OptionalFlow(
        actions=[MockAction(write_key="opt_key", write_value=99)]
    )
    basic.optional_flows = [optional]
    optional.context = basic.context

    run_flow(optional, make_request_flow())

    assert basic.context.get("opt_key") == 99

"""
note that we need to manually set optional flow context !!
"""

def test_multiple_optional_flows_share_basic_context():
    basic = BasicFlow(actions=[MockAction()])
    basic.context = FlowContext()
    
    opt1 = OptionalFlow(actions=[MockAction(write_key="a", write_value=1)])
    opt2 = OptionalFlow(actions=[MockAction(write_key="b", write_value=2)])

    opt1.context = basic.context
    opt2.context = basic.context

    run_flow(opt1, make_request_flow())
    run_flow(opt2, make_request_flow())

    assert basic.context.get("a") == 1
    assert basic.context.get("b") == 2



def test_fixed_flow_detects_independently():
    """
    this means that fixed flow is not affected by other flows
    """

    action = MockAction(pass_check=True,phase=Phase.RESPONSE)
    flow = FixedFlow(actions=[action])
    
    http_flow = make_response_flow()
    assert flow.matches(http_flow) is True


def test_fixed_flow_has_own_context():
    action = MockAction(write_key="fixed", write_value=True, phase=Phase.RESPONSE)
    flow = FixedFlow(actions=[action])
    flow.context = FlowContext()

    run_flow(flow, make_response_flow())

    assert flow.context.get("fixed") is True


def test_fixed_flow_context_is_never_shared():
    fixed = FixedFlow(actions=[MockAction()])
    basic = BasicFlow(actions=[MockAction()])

    fixed.context = FlowContext()
    basic.context = FlowContext()

    assert fixed.context is not basic.context


def test_fixed_flow_context_is_unique_per_run():
    """
    this means that fixed flow context is unique, and change each run
    """
    
    flow = FixedFlow(actions=[MockAction()])

    flow.context = FlowContext()
    ctx1 = flow.context

    flow.reset()
    flow.context = FlowContext()
    ctx2 = flow.context

    assert ctx1 is not ctx2


def test_request_only_action_runs_only_on_request():
    action = MockAction(phase=Phase.REQUEST)
    flow = BasicFlow(actions=[action])
    flow.context = FlowContext()

    run_flow(flow, make_request_flow())
    assert action.executed is True

    action.executed = False
    flow.reset()

    run_flow(flow, make_response_flow())
    assert action.executed is False


def test_response_only_action_runs_only_on_response():
    action = MockAction(phase=Phase.RESPONSE)
    flow = FixedFlow(actions=[action])
    flow.context = FlowContext()

    run_flow(flow, make_request_flow())
    assert action.executed is False

    flow.reset()
    run_flow(flow, make_response_flow())
    assert action.executed is True


def test_both_phase_action_runs_on_request_and_response():
    action = MockAction(phase=Phase.BOTH)
    flow = FixedFlow(actions=[action])
    flow.context = FlowContext()

    run_flow(flow, make_request_flow())
    assert action.executed is True

    action.executed = False
    flow.reset()

    run_flow(flow, make_response_flow())
    assert action.executed is True


def test_flow_is_finished():
    flow = FixedFlow(actions=[MockAction()])
    flow.context = FlowContext()

    assert flow.is_finished() is False
    run_flow(flow, make_request_flow())
    assert flow.is_finished() is True


"""
in case of context, we should set it manually, and manage it ourselves
"""
