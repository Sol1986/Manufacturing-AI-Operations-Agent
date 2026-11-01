
from typing import Literal, NotRequired, TypedDict


Intent = Literal[
    "equipment",
    "investigation",
    "action",
    "clarify",
]

# Define the parent state
class OpsPilotState(TypedDict):
    user_request: str

    intent: NotRequired[Intent]
    machine_id: NotRequired[str]

    request_id: NotRequired[str]
    issue: NotRequired[str]
    priority: NotRequired[str]

    agent_result: NotRequired[dict]
    final_response: NotRequired[str]

    pending_request: NotRequired[dict | None]
    clarification_resolved: NotRequired[bool]
