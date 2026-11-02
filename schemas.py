from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class EquipmentInput(BaseModel): # Basemodel Creates a Pydantic model that validates input data at runtime.
    machine_id: str = Field( # Defines a required string field. Adds a description explaining what the field represents.
        description="The unique equipment ID, such as M-103."
    )

class IntentClassification(BaseModel):
    intent: Literal[
        "equipment",
        "investigation",
        "action",
        "clarify",
    ]

    machine_id: str | None = Field(
        description=(
            "Machine identifier explicitly present "
            "in the user's request, if any."
        )
    )

    issue: str | None = Field(
        description="Maintenance issue, if identified."
    )

    priority: Literal[
        "low",
        "medium",
        "high",
    ] | None = None

class ClarificationAnswer(BaseModel):
    answers_question: bool = Field(
        description=(
            "True if the reply answers the clarifying question. "
            "False if it is a new or unrelated request."
        )
    )

    machine_id: str | None = Field(
        description=(
            "Machine identifier explicitly present "
            "in the user's reply, if any."
        )
    )

    issue: str | None = Field(
        description="Maintenance issue stated in the reply, if any."
    )

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