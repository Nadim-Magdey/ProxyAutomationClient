"""
mock data, include mock action and mock http_flow
"""

from typing import List
from FlowEngine.Actions import Action, Phase
from FlowEngine.FlowManager import Flow
from mitmproxy.test.tflow import tflow
from mitmproxy.http import Headers
import json
from mitmproxy.http import Response, Headers

class MockAction(Action):
    """
    mock class, for testing, with check and execute, and pass_check 
    to pass or fail check
    """

    def __init__(self, *, url_regex, phase = Phase.REQUEST, methods = None, params = None, pass_check:bool):
        super().__init__(url_regex=url_regex, phase=phase, methods=methods, params=params)
        self.pass_check = pass_check
        
    def execute(self, ctx, flow):
        pass

    def check(self, flow):
        return self.pass_check



def make_response_flow(status=200, headers=None, body=None):
    flow = tflow()
    # 🔑 explicitly create a response
    flow.response = Response.make(
        status_code=status,
        content=b"",
        headers=Headers(headers or {})
    )

    if body is not None:
        if isinstance(body, (dict, list)):
            flow.response.headers["content-type"] = "application/json"
            flow.response.content = json.dumps(body).encode()
        elif isinstance(body, bytes):
            flow.response.content = body
        else:
            flow.response.content = str(body).encode()

    return flow

def make_request_flow(url, headers=None, body=None):
    flow = tflow()

    # 🔑 explicitly create a request
    flow.request = tflow().request
    flow.request.url = url
    flow.request.headers = Headers(headers or {})
    if body is not None:
        if isinstance(body, (dict, list)):
            flow.request.headers["content-type"] = "application/json"
            flow.request.content = json.dumps(body).encode()
        elif isinstance(body, bytes):
            flow.request.content = body
        else:
            flow.request.content = str(body).encode()

    return flow

if __name__ == "__main__":
    mock_http_flow = tflow()
    print(mock_http_flow.request.url)

    print(mock_http_flow.request.headers)

    print(mock_http_flow.request.content)

    print(mock_http_flow.request.text)

    action = MockAction(url_regex=".*", pass_check=False)
    print(action.check(mock_http_flow))

    flow = Flow(actions=[action])
    print(flow.check_next(mock_http_flow))

    action = MockAction(url_regex=".*", pass_check=True)
    print(f"action check {action.check(mock_http_flow)}")

    flow = Flow(actions=[action])
    print(f"check next", flow.check_next(mock_http_flow))
    # print http_flow components, req and res
    http_flow = make_response_flow(status=200, body="test")
    print(f"http flow url {http_flow.request.url}")

    print(f"http flow headers {http_flow.request.headers}")
    print("response content", http_flow.response.content)

    flow = Flow(actions=[action])
    print(f"check next", flow.check_next(http_flow))

