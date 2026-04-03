import threading
import time
import asyncio
from typing import Optional
from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster
from mitmproxy.master import Master
from .Addon import ProxyAddon 
from .Rules import EditBody, EditQueryRule, ExtractBodyElementRule,ExtractHeaderVariable, DetectRule, ExtractQueryRule,Reject, Redirect, Forward, ChangeBody, EditHeaders, RemoveBodyElementRule, RemoveHeaderRule, RemoveQueryRule, RuleTypes, RulePhase, RuleStatus, Methods

class ProxyInterface:
    def __init__(self, host="127.0.0.1", port=8080):
        self.addon = ProxyAddon()
        self.host = host
        self.port = port
        self.master: Optional[Master] = None
        
    def start(self):
        if self.master:
            print("proxy already running.")
            return
        
        options = Options(listen_host=self.host, listen_port=self.port)

        def run_proxy():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def start_master():
                master = DumpMaster(options, with_termlog=False)
                self.master = master
                master.addons.add(self.addon)
                await master.run()

            try:
                loop.run_until_complete(start_master())
            except asyncio.CancelledError:
                pass
            finally:
                loop.close()

        self.thread = threading.Thread(target=run_proxy, daemon=True)
        self.thread.start()
        time.sleep(0.3)
        print(f"proxy run at {self.host}:{self.port}")

    def stop(self):
        if not self.master:
            return
        
        self.master.shutdown()
        self.thread.join(timeout=3)
        self.master = None
        self.thread = None
        print(" proxy stopped.")
    
    def add_rule(self, rule_type:RuleTypes,method :Methods, phase:RulePhase,url_regix:str , callback_function, context,params =None,values=None, content=None,distinations=None, header_key:str=None,element_regix=None,return_name=None, new_value=None, query_key=None):
        if rule_type == RuleTypes.Detect.value:
            rule = DetectRule(
                method=method,
                rule_phase=phase,
                url_regix=url_regix,
                context=context,
                callback=callback_function,
            )

        elif rule_type == RuleTypes.ExtractQuery.value:
            rule = ExtractQueryRule(
                method=method,
                rule_phase=phase,
                url_regix=url_regix,
                context=context,
                callback=callback_function,
                query_key=query_key
            )

        elif rule_type == RuleTypes.EditQuery.value:
            rule = EditQueryRule(
                method=method,
                rule_phase=phase,
                url_regix=url_regix,
                context=context,
                callback=callback_function,
                param_key=params,
                new_value=new_value
            )
        elif rule_type == RuleTypes.RemoveQueryRule.value:
            rule = RemoveQueryRule(
                method=method,
                rule_phase=phase,
                url_regix=url_regix,
                context=context,
                callback=callback_function,
                param_key=params
            )

        elif rule_type == RuleTypes.Reject.value:
            rule = Reject(
            url_regix=url_regix,
            method=method,
            rule_phase=phase,
            context=context,
            callback=callback_function
            )

        elif rule_type == RuleTypes.EditBody.value:
            rule = EditBody(
                callback=callback_function,
                url_regix=url_regix,
                method=method,
                rule_phase=phase,
                context=context,
                element_regix=element_regix,
                new_value=new_value
            )

        elif rule_type == RuleTypes.RemoveBodyElement.value:
            rule = RemoveBodyElementRule(
                callback=callback_function,
                url_regix=url_regix,
                method=method,
                rule_phase=phase,
                context=context,
                element_regix=element_regix
            )
        elif rule_type == RuleTypes.EditHeader.value:
            rule = EditHeaders(
            url_regix=url_regix,
            rule_phase=phase,
            method = method,
            callback=callback_function,
            context=context,
            values=values
            )
            
        elif rule_type == RuleTypes.RemoveHeaderRule.value:
            rule = RemoveHeaderRule(
            url_regix=url_regix,
            rule_phase=phase,
            method = method,
            callback=callback_function,
            context=context,
            header_key=header_key
            )
        
        elif rule_type == RuleTypes.ChangeBody.value:
            rule = ChangeBody(
            url_regix=url_regix,
            rule_phase=phase,
            method = method,
            callback=callback_function,
            context=context,

            content=content
            )
        
        elif rule_type == RuleTypes.Redirect.value:
            rule = Redirect(
            url_regix=url_regix,
            rule_phase=phase,
            method = method,
            callback=callback_function,
            context=context,

            distination=distinations
            )
        elif rule_type == RuleTypes.ExtractHeaderVariable.value:
            rule = ExtractHeaderVariable(
            url_regix=url_regix,
            rule_phase=phase,
            method = method,
            callback=callback_function,
            context=context,

            header_key= header_key            
            )

        elif rule_type == RuleTypes.ExctractBodyElement.value:
            print("create extract body element ..........................")
            rule = ExtractBodyElementRule(
            url_regix=url_regix,
            rule_phase=phase,
            method = method,
            callback=callback_function,
            context=context,
            element_regix=element_regix,
            return_name=return_name
            )

        else:
            raise Exception("Rule not found ")

        self.addon.add_rule(rule=rule)
        print(f"rule {str(rule_type)} added successfully")
