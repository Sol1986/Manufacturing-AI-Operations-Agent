from typing import Literal, NotRequired, TypedDict
class State(TypedDict):
    user_request: str

    intent: NotRequired[Literal[
    "equipment",
    "investigation",
    "action",
    "clarify",
]]
    machine_id: NotRequired[str]

    request_id: NotRequired[str]
    issue: NotRequired[str]
    priority: NotRequired[str]

    agent_result: NotRequired[dict]
    final_response: NotRequired[str]

    pending_request: NotRequired[dict | None]
    clarification_resolved: NotRequired[bool]
    missing_fields: NotRequired[list[str]]
    last_machine_id: NotRequired[str]

