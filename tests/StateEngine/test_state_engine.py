"""
State machine invariants

These should always be true:

Exactly one state is active at a time

assert isinstance(runtime.state, FlowState)


Only one active flow at a time

runtime.active_flow is None or runtime.active_flow in (
    runtime.basic_flows
    + runtime.optional_flows
    + runtime.fixed_flows
)


State transitions are explicit

Every handle() must:

Either change runtime.state

Or intentionally keep it the same

No hidden transitions inside flows/actions

Actions execute in strict order

next_action() is called once per action

No skipping

No re-execution unless explicitly designed
"""

import pytest

from FlowEngine.StateEngine import FlowRuntime
from FlowEngine.StateEngine import FlowState
from FlowEngine.StateEngine import IdleState
from FlowEngine.StateEngine import SearchForBasicFlowState
from FlowEngine.StateEngine import SearchForOptionalFlowState

from FlowEngine.FlowManager import BasicFlow
from FlowEngine.FlowManager import OptionalFlow
from FlowEngine.FlowManager import FixedFlow

from FlowEngine.Actions import DetectAction
from FlowEngine.Actions import EditHeadersAction
from FlowEngine.Actions import ExtractQueryAction
from FlowEngine.Actions import RedirectAction
