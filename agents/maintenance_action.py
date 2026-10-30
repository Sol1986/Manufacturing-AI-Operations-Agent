
from typing import Literal, NotRequired, TypedDict

from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, ConfigDict, Field

# Define the maintenance action state
class ActionState(TypedDict):
    request_id: str
    machine_id: str
    issue: str
    priority: str

    proposed_work_order: NotRequired[dict]
    approval_action: NotRequired[str]
    approval_decision: NotRequired[dict]

    status: NotRequired[str]
    work_order_id: NotRequired[str]
    final_result: NotRequired[dict]


# Define the approval schema
class WorkOrderChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: Literal[
        "low",
        "medium",
        "high",
    ] | None = None

    estimated_minutes: int | None = Field(
        default=None,
        ge=15,
        le=480,
    )

    action: str | None = Field(
        default=None,
        min_length=5,
        max_length=200,
    )


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "approve",
        "reject",
        "edit",
    ]

    changes: WorkOrderChanges | None = None

    reviewer_id: str = Field(min_length=1)


# Create the proposal node. The first node prepares the work order.
def prepare_work_order(state: ActionState) -> dict:
    proposal = {
        "request_id": state["request_id"],
        "machine_id": state["machine_id"],
        "issue": state["issue"],
        "priority": state["priority"],
        "action": "Inspect and repair the cooling system.",
        "estimated_minutes": 120,
    }

    return {
        "proposed_work_order": proposal,
        "status": "awaiting_approval",
    }



from langgraph.types import interrupt

# Create the human approval node
# 1. This defines a standard Python function named 'request_approval'.
# It takes in the current graph memory ('state') and promises to return a dictionary ('-> dict').
def request_approval(state: ActionState) -> dict:

    # 2. This creates a hard breakpoint. The entire AI agent FREEZES right here. 
    # It sends the JSON data below out to a user interface and waits for a human response.
    decision = interrupt(
        {
            # Tells the frontend UI what kind of box to display to the human user.
            "type": "maintenance_approval",
            
            # Grabs the planned work order out of the graph memory to show it to the human.
            "proposal": state["proposed_work_order"],
            
            # Dictates the exact buttons the human is allowed to click on their screen.
            "allowed_actions": [
                "approve",
                "reject",
                "edit",
            ],
        }
    ) # 3. When a human finally clicks a button, their choice lands right here in the 'decision' variable.

    # 4. This takes whatever the human sent back and runs it through a Pydantic safety check
    # to guarantee the data isn't corrupt, blank, or containing typos.
    validated = ApprovalDecision.model_validate(
        decision
    )

    # 5. This tells the function what data to send back into the main graph's central memory.
    return {
        # Extracts the clean, verified action (like "approve") from the validator.
        "approval_action": validated.action,
        
        # Converts the entire validation object back into a standard dictionary format to save it.
        "approval_decision": validated.model_dump(),
    }



# Route the approval decision
def route_decision(state: ActionState) -> str:
    action = state["approval_action"]

    if action == "approve":
        return "execute"

    if action == "reject":
        return "reject"

    return "revise"


# Handle proposal edits
def revise_proposal(state: ActionState) -> dict:
    decision = state["approval_decision"]

    changes = decision.get("changes") or {}

    updated_proposal = {
        **state["proposed_work_order"],
        **{
            key: value
            for key, value in changes.items()
            if value is not None
        },
    }

    return {
        "proposed_work_order": updated_proposal,
        "status": "awaiting_approval",
    }


from old.work_orders import create_work_order

# Create the execution node
def execute_work_order(state: ActionState) -> dict:
    if state["approval_action"] != "approve":
        raise ValueError(
            "Work order cannot execute without approval."
        )

    record = create_work_order(
        request_id=state["request_id"],
        proposal=state["proposed_work_order"],
    )

    return {
        "status": "created",
        "work_order_id": record["work_order_id"],
    }


# Create the rejection node
def reject_work_order(state: ActionState) -> dict:
    return {
        "status": "rejected",
    }


# Create the final result node
def finalize_action(state: ActionState) -> dict:
    result = {
        "request_id": state["request_id"],
        "machine_id": state["machine_id"],
        "status": state["status"],
        "work_order_id": state.get("work_order_id"),
    }

    return {
        "final_result": result
    }



# Now connect everything.
builder = StateGraph(ActionState)

builder.add_node("prepare", prepare_work_order)
builder.add_node("approval", request_approval)
builder.add_node("revise", revise_proposal)
builder.add_node("execute", execute_work_order)
builder.add_node("reject", reject_work_order)
builder.add_node("finalize", finalize_action)


builder.add_edge(START, "prepare")
builder.add_edge("prepare", "approval")


builder.add_conditional_edges(
    "approval",
    route_decision,
    {
        "execute": "execute",
        "reject": "reject",
        "revise": "revise",
    },
)


builder.add_edge("revise", "approval")
builder.add_edge("execute", "finalize")
builder.add_edge("reject", "finalize")
builder.add_edge("finalize", END)


maintenance_action_graph = builder.compile()

