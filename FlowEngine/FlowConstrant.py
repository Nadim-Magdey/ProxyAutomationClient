from typing import List


class ConstraintResult:
    def __init__(self, accepted: bool, reason_message: str | None = None):
        self.accepted = accepted
        self.reason_message = reason_message


class FlowConstraint:

    def __init__(self, left: str, right: str):
        self.left = left
        self.right = right

    def conflicts(self, a: str, b: str):

        result = (
            (a == self.left and b == self.right) or
            (a == self.right and b == self.left)
        )

        if result:
            reason = f"{a} and {b} are conflicting flows"
            return True, reason

        return False, None


class ConstraintLoader:

    @staticmethod
    def load(api_constraints: list[dict]) -> List[FlowConstraint]:

        constraints: List[FlowConstraint] = []

        for c in api_constraints:
            constraints.append(
                FlowConstraint(
                    left=c["left_flow"],
                    right=c["right_flow"]
                )
            )

        return constraints


    @staticmethod
    def check(constraints: List[FlowConstraint], a: str, b: str) -> ConstraintResult:

        for constraint in constraints:

            conflict, reason = constraint.conflicts(a, b)

            if conflict:
                return ConstraintResult(False, reason)

        return ConstraintResult(True, None)
