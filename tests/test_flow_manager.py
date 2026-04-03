from types import SimpleNamespace

from FlowEngine.FlowManager import Flow, BasicFlow, OptionalFlow, FixedFlow, FlowManager
from FlowEngine.Actions import (
    DetectAction,
    EditHeadersAction,
    ExtractQueryAction,
    RedirectAction,
    ActionResult,
    Phase,
)


class MockRequest:
    def __init__(self, url):
        self.url = url
        self.headers = {}

    def get_text(self):
        return ""

    def set_text(self, text):
        pass


class MockResponse:
    def __init__(self):
        self.headers = {}
        self.status_code = 200
        self.content = b""


class MockFlow:
    def __init__(self, url):
        self.request = MockRequest(url)
        self.response = MockResponse()

    def kill(self):
        print("[MockFlow] Request killed")



from FlowEngine.Actions import Action

class PrintAction(Action):
    name = "print"
    phase = Phase.BOTH

    def check(self, ctx):
        return True

    def execute(self, ctx):
        print(f"[Action] {self.params.get('msg')}")
        return ActionResult.continue_()



optional_login_flow = OptionalFlow(
    name="optional-login",
    actions=[
        DetectAction({"url_regex": "/login"}),
        PrintAction({"msg": "Optional login flow executed"}),
    ],
)


basic_api_flow = BasicFlow(
    name="basic-api",
    actions=[
        DetectAction({"url_regex": "/api"}),
        ExtractQueryAction({"query_key": "token"}),
        PrintAction({"msg": "API basic flow running"}),
    ],
    optional_flows=[optional_login_flow],
)

basic_admin_flow = BasicFlow(
    name="basic-admin",
    actions=[
        DetectAction({"url_regex": "/admin"}),
        RedirectAction({"destination": "https://example.com/403"}),
        PrintAction({"msg": "Admin redirected"}),
    ],
)

fixed_flow = FixedFlow(
    name="fixed",
    actions=[
        PrintAction({"msg": "Fixed flow executed"}),
    ],
)

manager = FlowManager()
manager.add_basic_flow(basic_api_flow)
manager.add_basic_flow(basic_admin_flow)
manager.set_fixed_flow(fixed_flow)

# Optional GUI hook simulation
manager.on_basic_detected = lambda flow: print(
    f"[GUI] Basic flow detected: {flow.name}"
)

requests = [
    "/api?token=123",
    "/api/login",
    "/api/data",
]

for i, url in enumerate(requests, 1):
    print(f"\n========== REQUEST {i}: {url} ==========")
    flow = MockFlow(url)
    manager.handle_request(flow)
