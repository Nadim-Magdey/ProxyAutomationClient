from typing import Dict, List, Any
from .Actions import ACTION_MAP, Action
from .custom_types import Phase

from typing import Dict, Any

class ActionFactory:

    @staticmethod
    def from_json(step):
        action_name = step["action"]
        params = step.get("params", {})
        log = step.get("log", False)
        params["log"] = log
        
        action_cls = ACTION_MAP.get(action_name)
        if not action_cls:
            raise ValueError(f"Unknown action: {action_name}")

        # 🔥 Normalize new_value
        if "new_value" in params and isinstance(params["new_value"], dict):
            nv = params["new_value"]

            if nv.get("type") == "variable":
                params["new_value"] = nv.get("value")   # keep {{asd}}

            elif nv.get("type") == "fixed":
                params["new_value"] = nv.get("value")   # plain value

        phase = Phase(params.get("phase", "request").lower())

        action_instance = action_cls(
            url_regex=params.get("url_regix", ".*"),
            phase=phase,
            methods=[params["method"]] if "method" in params else None,
            params=params,
        )
        
        action_instance.log_enabled = log

        return action_instance

    @staticmethod
    def list_from_json(flow_json: Dict[str, Any]) -> List[Action]:
        """
        Convert steps[] → list[Action]
        """
        return [
            ActionFactory.from_json(step)
            for step in flow_json.get("steps", [])
        ]



if __name__ == "__main__":
    pass
