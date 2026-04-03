import json
from typing import Dict, Any, List
from .flow_factory import ActionFactory
from .FlowManager import Flow, BasicFlow, OptionalFlow, FixedFlow


class FlowBuilder:
    """
    Converts DB / API JSON to real Flow objects
    """

    @staticmethod
    def build_basic_flow(
        *,
        name: str,
        flow_json: Dict[str, Any],
        inputs: Dict[str, Any] | None = None,
        optional_flows: List[Dict[str, Any]] | None = None,
    ) -> BasicFlow:
        
        actions = ActionFactory.list_from_json(flow_json)
        
        opt_flows: List[OptionalFlow] = []
        for opt in optional_flows or []:
            opt_actions = ActionFactory.list_from_json(opt["flows"])
            opt_flows.append(
                OptionalFlow(
                    actions=opt_actions,
                    name=opt["name"],
                )
            )

        return BasicFlow(
            actions=actions,
            optional_flows=opt_flows,
            name=name,
            inputs=inputs,
        )

    @staticmethod
    def build_fixed_flow(
        *,
        name: str,
        flow_json: Dict[str, Any],
    ) -> FixedFlow:
        notification_condition = flow_json.get("notification_condition")
        success_value = flow_json.get("success_value")
        notify_variables = flow_json.get("notify_variables")
        
        actions = ActionFactory.list_from_json(flow_json)
        return FixedFlow(actions=actions, name=name, 
                         notify_condition=notification_condition
                         ,success_value=success_value
                         ,notify_variables=notify_variables)

    @staticmethod
    def build_optional_flow(
        *,
        name: str,
        flow_json: Dict[str, Any],
    ) -> OptionalFlow:
        
        actions = ActionFactory.list_from_json(flow_json)
        return OptionalFlow(actions=actions, name=name)
    
# test

if __name__ == "__main__":
    api_data = {
    "services": [
        {
            "id": 5,
            "name": "sadasd",
            "inputs": [
                {
                    "name": "asd",
                    "type": "text",
                    "constraints": {}
                }
            ],
            "flows": {
                "steps": [
                    {
                        "action": "edit_body",
                        "log": False,
                        "params": {
                            "method": "GET",
                            "url_regix": "asd",
                            "phase": "request",
                            "element_regix": "asd",
                            "new_value": {
                                "type": "variable",
                                "value": "{{aa}}"
                            }
                        }
                    }
                ]
            },
            "optional_flows": []
        }
    ],
    "user_optional_flows": [],
    "user_fixed_flows": []
}
    
    flow = FlowBuilder.build_basic_flow(
        name="sadasd",
        flow_json=api_data["services"][0]["flows"],
        inputs=api_data["services"][0]["inputs"],
        optional_flows=api_data["services"][0]["optional_flows"],
    )
    print(flow.actions[0].params)
    