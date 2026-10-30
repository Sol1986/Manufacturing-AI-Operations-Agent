
from typing import Annotated, NotRequired, TypedDict
import operator
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END


class InvestigationState(TypedDict):
    machine_id: str

    equipment_data: NotRequired[dict]
    maintenance_data: NotRequired[dict]
    production_data: NotRequired[dict]
    incident_data: NotRequired[dict]

    findings: Annotated[list[dict], operator.add]

    investigation_report: NotRequired[dict]


# Now we need to combine the findings into one structured report.
# We'll use a Pydantic model to validate the report's structure.


class InvestigationReport(BaseModel):
    machine_id: str
    findings: list[dict]
    risk_level: str
    recommendation: str
    evidence_sources: list[str] = Field(
        default_factory=list # If someone creates this object without specifying any evidence sources, automatically run the list() function to generate a fresh, empty list [] for them.
    )

'''
With the default: You can safely initialize your agent state with just the user's query (AgentState(query="Hello")). 
Pydantic quietly builds the empty list [] behind the scenes, keeping your code running smoothly.
'''

# Create our simulated manufacturing data
EQUIPMENT_DB = {
    "M-103": {
        "status": "Maintenance Required",
        "temperature_c": 85.5,
    }
}

MAINTENANCE_DB = {
    "M-103": {
        "recent_repairs": 3,
        "recurring_issue": "Cooling system",
    }
}

PRODUCTION_DB = {
    "M-103": {
        "target_units": 1000,
        "actual_units": 820,
        "downtime_minutes": 95,
    }
}

INCIDENT_DB = {
    "M-103": {
        "recent_incidents": 2,
        "incident_type": "Overheating",
    }
}

# Build the four parallel investigation nodes
import asyncio


async def check_equipment( # The node reads machine_id, retrieves the equipment record, and returns two state updates.
    state: InvestigationState,
) -> dict:
    machine_id = state["machine_id"]

    await asyncio.sleep(1)

    equipment = EQUIPMENT_DB[machine_id]

    return {
        "equipment_data": equipment,
        "findings": [
            {
                "source": "equipment",
                "detail": (
                    f"Temperature is "
                    f"{equipment['temperature_c']}°C."
                ),
            }
        ],
    }

# Now maintenance:
async def check_maintenance(
    state: InvestigationState,
) -> dict:
    machine_id = state["machine_id"]

    await asyncio.sleep(1)

    maintenance = MAINTENANCE_DB[machine_id]

    return {
        "maintenance_data": maintenance,
        "findings": [
            {
                "source": "maintenance",
                "detail": (
                    "Recurring cooling system issue "
                    "with three recent repairs."
                ),
            }
        ],
    }

# Production:
async def check_production(
    state: InvestigationState,
) -> dict:
    machine_id = state["machine_id"]

    await asyncio.sleep(1)

    production = PRODUCTION_DB[machine_id]

    target = production["target_units"]
    actual = production["actual_units"]

    decline_pct = (
        (target - actual) / target
    ) * 100

    return {
        "production_data": production,
        "findings": [
            {
                "source": "production",
                "detail": (
                    f"Production is {decline_pct:.1f}% "
                    "below target."
                ),
            }
        ],
    }

# And incidents:
async def check_incidents(
    state: InvestigationState,
) -> dict:
    machine_id = state["machine_id"]

    await asyncio.sleep(1)

    incidents = INCIDENT_DB[machine_id]

    return {
        "incident_data": incidents,
        "findings": [
            {
                "source": "incidents",
                "detail": (
                    "Two recent overheating "
                    "incidents were recorded."
                ),
            }
        ],
    }

'''
Each node:
1. Receives the same InvestigationState.
2. Reads the machine ID.
3. Performs an independent lookup.
4. Returns its own structured data.
5. Appends one finding.
'''



# Now create the aggregation node:
def combine_evidence(state: InvestigationState) -> dict:
    """Combine the four research branches."""

    equipment = state["equipment_data"]
    maintenance = state["maintenance_data"]
    production = state["production_data"]
    incidents = state["incident_data"]

    findings = sorted(
        state["findings"],
        key=lambda item: item["source"],
    )

    if (
        equipment["temperature_c"] >= 85
        and incidents["recent_incidents"] >= 2
    ):
        risk_level = "high"
    else:
        risk_level = "medium"

    report = InvestigationReport(
        machine_id=state["machine_id"],
        findings=findings,
        risk_level=risk_level,
        recommendation=(
            "Schedule a maintenance review of the "
            "cooling system and temperature sensors."
        ),
        evidence_sources=[
            "equipment",
            "maintenance",
            "production",
            "incidents",
        ],
    )

    return {
        "investigation_report": report.model_dump()
    }

# Build the Investigation Agent subgraph
builder = StateGraph(InvestigationState)

builder.add_node("equipment", check_equipment)
builder.add_node("maintenance", check_maintenance)
builder.add_node("production", check_production)
builder.add_node("incidents", check_incidents)
builder.add_node("combine", combine_evidence)


# Fan-out
builder.add_edge(START, "equipment")
builder.add_edge(START, "maintenance")
builder.add_edge(START, "production")
builder.add_edge(START, "incidents")


# Fan-in: wait for all four branches
builder.add_edge( # It creates a waiting edge. And because the branches are asynchronous, their simulated one-second waits can overlap.
    [
        "equipment",
        "maintenance",
        "production",
        "incidents",
    ],
    "combine",
)


builder.add_edge("combine", END)

investigation_graph = builder.compile()



