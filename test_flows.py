from FlowEngine.FlowManager import FlowManager, BasicFlow, OptionalFlow, FixedFlow
from FlowEngine.Actions import (
    DetectAction, EditBodyAction, EditHeadersAction, RejectAction,
    RedirectAction, ForwardAction, RemoveBodyElementAction, ChangeBodyAction,
    ExtractHeaderVariableAction, RemoveHeaderAction, ExtractBodyElementAction,
    ExtractQueryAction, EditQueryAction, RemoveQueryAction, Phase
)
from FlowEngine.StateEngine import FlowRuntime, PassThroughState

class Request:
    def __init__(self, url, method="GET", body="", headers=None):
        self.url = url
        self.method = method.upper()
        self.body = body
        self.headers = headers or {}

    def get_text(self):
        return self.body

    def set_text(self, new_body):
        self.body = new_body

class Response:
    def __init__(self):
        self.body = ""
        self.status_code = 200

    def get_text(self):
        return self.body

    def set_text(self, new_body):
        self.body = new_body

class HTTPFlow:
    def __init__(self, url, method="GET", body="", headers=None):
        self.request = Request(url, method, body, headers)
        self.response = Response()
        self.killed = False

    def kill(self):
        self.killed = True

def print_step(flow_name, action_name, ctx):
    print(f"[{flow_name}] {action_name}")
    print(f"URL: {ctx.flow.request.url}")
    print(f"Body: {ctx.flow.request.body}")
    print(f"Headers: {ctx.flow.request.headers}")
    print(f"Context: {ctx.data}")
    print("-" * 60)

basic_payment_flow = BasicFlow(
    name="cybersource_payment",
    actions=[
        DetectAction(url_regex=r"/pay/start", phase=Phase.REQUEST),
        ExtractQueryAction(params={"query_key": "session"}, url_regex=r"/pay/start"),
        EditHeadersAction(params={"values": {"X-Service": "CyberSource"}}, url_regex=r"/pay/start"),
        ForwardAction(url_regex=r"/pay/start"),
        EditBodyAction(params={"element_regex": r"amount", "new_value": "100"}, url_regex=r"/pay/start"),
    ]
)

otp_optional_flow = OptionalFlow(
    name="otp_flow",
    actions=[
        DetectAction(url_regex=r"/otp", phase=Phase.REQUEST),
        EditHeadersAction(params={"values": {"X-OTP": "required"}}, url_regex=r"/otp"),
        ExtractBodyElementAction(params={"element_regex": r"code", "return_name": "otp_code"}, url_regex=r"/otp"),
        ForwardAction(url_regex=r"/otp"),
    ]
)

basic_payment_flow.optional_flows = [otp_optional_flow]

basic_confirm_flow = BasicFlow(
    name="payment_confirm",
    actions=[
        DetectAction(url_regex=r"/pay/confirm", phase=Phase.REQUEST),
        ExtractBodyElementAction(params={"element_regex": r"status", "return_name": "status"}, url_regex=r"/pay/confirm"),
        ForwardAction(url_regex=r"/pay/confirm"),
    ]
)

confirm_log_optional = OptionalFlow(
    name="confirm_log",
    actions=[
        DetectAction(url_regex=r"/pay/confirm", phase=Phase.REQUEST),
        EditHeadersAction(params={"values": {"X-Log": "confirmed"}}, url_regex=r"/pay/confirm"),
    ]
)

basic_confirm_flow.optional_flows = [confirm_log_optional]

fixed_result_flow = FixedFlow(
    name="payment_result",
    actions=[
        ChangeBodyAction(params={"content": "[PAYMENT COMPLETED]"}, url_regex=r".*"),
        EditHeadersAction(params={"values": {"X-Payment": "done"}}, url_regex=r".*"),
    ]
)


manager = FlowManager()
manager.add_basic_flow(basic_payment_flow)
manager.add_basic_flow(basic_confirm_flow)
manager.set_fixed_flow(fixed_result_flow)


for flow in manager.basic_flows + [manager.fixed_flow]:
    for action in flow.actions:
        old_execute = action.execute
        def wrapped(ctx, action=action, flow=flow):
            result = old_execute(ctx)
            print_step(flow.name, action.name, ctx)
            return result
        action.execute = wrapped


requests = [
    HTTPFlow("/pay/start?session=abc", body="amount=50"),
    HTTPFlow("/otp", body="code=123456"),
    HTTPFlow("/pay/confirm", body="status=OK"),
]


for req in requests:
    runtime  = FlowRuntime.getInstance(manager, req, Phase.REQUEST)
    print(f"request to {req.request.url} sent")
    
    while not isinstance(runtime.state, PassThroughState):
        runtime.step()
