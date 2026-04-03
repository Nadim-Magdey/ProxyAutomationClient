from typing import Dict, List, Tuple, Any
from .flow_factory import ActionFactory
from .FlowManager import BasicFlow, OptionalFlow, FixedFlow

class RuntimeFlowLoader:
    """
    Converts API response JSON into runtime Flow objects
    """

    @staticmethod
    def load(response: Dict[str, Any]) -> Tuple[
        List[BasicFlow],
        List[OptionalFlow],
        List[FixedFlow],
    ]:
        """
        Returns:
            basic_flows,
            user_optional_flows,
            fixed_flows

            basic flows include optional flows
            
        """

        basic_flows: List[BasicFlow] = []
        user_optional_flows: List[OptionalFlow] = []
        fixed_flows: List[FixedFlow] = []

        for service in response.get("services", []):

            actions = ActionFactory.list_from_json(service["flows"])
            group  = service.get("group")
            optional_flows = []
            for opt in service.get("optional_flows", []):
                opt_group = opt.get("group")
                opt_actions = ActionFactory.list_from_json(opt["flows"])
                optional_flows.append(
                    OptionalFlow(
                        actions=opt_actions,
                        name=opt["name"],
                        group=opt_group
                    )
                )

            basic_flows.append(
                BasicFlow(
                    name=service["name"],
                    actions=actions,
                    optional_flows=optional_flows,
                    inputs=service.get("inputs"),
                    group=group
                )
            )


        for opt in response.get("user_optional_flows", []):
            actions = ActionFactory.list_from_json(opt["flows"])
            group = opt.get("group")
            user_optional_flows.append(
                OptionalFlow(
                    actions=actions,
                    name=opt["name"],
                    group = group
                )
            )

 
        for fixed in response.get("user_fixed_flows", []):
            actions = ActionFactory.list_from_json(fixed["flows"])
            group = fixed.get("group")
            fixed_flows.append(
                FixedFlow(
                    actions=actions,
                    name=fixed["name"],
                    notify_condition=fixed["notify_condition"],
                    success_value=fixed["success_value"],
                    notify_variables=fixed["notify_variables"],
                    group=group
                )
            )
        # load flow_constraints
        constrains = response.get("flow_constraints", [])

        return basic_flows, user_optional_flows, fixed_flows, constrains


if __name__ == "__main__":
    api_data = {'services': [{'id': 1, 'name': 'b1', 'inputs': {'inputs': [{'name': 'i1', 'type': 'text', 'constraints': {}}]}, 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': '21', 'phase': 'request'}}, {'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'w2', 'phase': 'request'}}]}, 'optional_flows': [{'id': 1, 'name': 'o1', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'step1.com', 'phase': 'request'}}, {'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'dasd', 'phase': 'request'}}]}, 'order': 0}, {'id': 2, 'name': 'o2', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'zxcv', 'phase': 'request'}}]}, 'order': 0}]}, {'id': 3, 'name': 'b2', 'inputs': {'inputs': [{'name': 'das', 'type': 'text', 'constraints': {}}]}, 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'dasdas', 'phase': 'request'}}]}, 'optional_flows': [{'id': 2, 'name': 'o2', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'zxcv', 'phase': 'request'}}]}, 'order': 0}]}], 'user_optional_flows': [{'id': 1, 'name': 'o1', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'step1.com', 'phase': 'request'}}, {'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'dasd', 'phase': 'request'}}]}, 'order': 0}, {'id': 2, 'name': 'o2', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'zxcv', 'phase': 'request'}}]}, 'order': 0}, {'id': 3, 'name': 'io', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'das', 'phase': 'request'}}]}, 'order': 0}, {'id': 4, 'name': 'io2', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'dasd', 'phase': 'request'}}]}, 'order': 0}], 'user_fixed_flows': [{'id': 1, 'name': 'f1', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'f1', 'phase': 'request'}}]}, 'order': 0}, {'id': 2, 'name': 'f1', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'adsf', 'phase': 'request'}}]}, 'order': 0}, {'id': 3, 'name': 'wasd', 'flows': {'steps': [{'action': 'detect', 'params': {'method': 'GET', 'url_regix': 'asd', 'phase': 'request'}}]}, 'order': 0}]}

    basic_flows, user_optional_flows, fixed_flows = RuntimeFlowLoader.load(api_data)

    print("basic_flows", basic_flows)
    print("user_optional_flows", user_optional_flows)
    print("fixed_flows", fixed_flows)
    
    #print basic flows 
    print("basic flow names")
    for basic in basic_flows:
        print(basic.name)
        print("its optioan lnames ")
        for opt in basic.optional_flows:
            print(opt.name)
    
    print("optional flows names")
    for opt in user_optional_flows:
            print(opt.name)

    for fixed in fixed_flows:
        print(fixed.name)
        