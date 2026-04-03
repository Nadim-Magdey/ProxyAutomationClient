from FlowEngine.FlowManager import FlowManager
from ProxyEngine.Rules import RulePhase
from mitmproxy.http import HTTPFlow


class ClientAddon:
    def __init__(self, flow_manager: FlowManager):
        self.manager = flow_manager
        
    def request(self, flow: HTTPFlow):
        # print(f"request {flow}")       
        self.manager.handle_request(flow)
        return
        
    def response(self, flow):
        # url = flow.response.url if flow.response else flow.request.url        
        # if "secureacceptance.cybersource.com" != url:
        #     return   
         
        self.manager.handle_request(flow)
        # print(f"response {flow}")
        return

    def error(self, flow):
        print(f"error with flow {flow}")
        return

