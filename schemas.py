
from typing import Literal

from pydantic import BaseModel, Field

# We'll use an LLM with structured output. We need to distinguish between reading information and taking action.
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
