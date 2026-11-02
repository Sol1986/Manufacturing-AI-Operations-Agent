#--------------------------------------------
# IMPORTS & CONFIGURATION
#--------------------------------------------
from typing import Annotated, NotRequired, TypedDict
import operator
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from tools.equipment_db import EQUIPMENT_DB, PRODUCTION_DB, MAINTENANCE_DB, INCIDENT_DB

#--------------------------------------------
# STATE
#--------------------------------------------
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
    evidence_sources: list[str]

#--------------------------------------------
# TOOLS 
#--------------------------------------------
#NA


#--------------------------------------------
# NODES
#--------------------------------------------

# # The node reads machine_id, retrieves the equipment record, and returns two state updates.
async def check_equipment(state: InvestigationState) -> dict:
    machine_id = state["machine_id"]

    equipment = EQUIPMENT_DB[machine_id]

    return {
        "equipment_data": equipment,
        "findings": [
            {
                "source": "equipment",
                "detail": (
                    f"Temperature is "
                    f"{equipment['temperature']}°C."
                ),
            }
        ],
    }

# # The node reads machine_id, retrieves the maintenance record, and returns two state updates.
async def check_maintenance(state: InvestigationState) -> dict:
    machine_id = state["machine_id"]

    maintenance = MAINTENANCE_DB[machine_id]

    repair_count = sum(
            record["type"] == "repair"
            for record in maintenance["history"]
        )

    return {
        "maintenance_data": maintenance,
        "findings": [
            {
                "source": "maintenance",
                "detail": (
                    f"Recurring {maintenance['recurring_issue']} issue "
                    f"with {repair_count} recent repairs."
                ),
            }
        ],
    }

# # The node reads machine_id, retrieves the incident record, and returns two state updates.
async def check_production(
    state: InvestigationState,
) -> dict:
    machine_id = state["machine_id"]

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

async def check_incidents(state: InvestigationState) -> dict:
    machine_id = state["machine_id"]

    incidents = INCIDENT_DB[machine_id]

    return {
        "incident_data": incidents,
        "findings": [
            {
                "source": "incidents",
                "detail": (
                    f"Two recent {incidents['incident_type'].lower()} "
                    "incidents were recorded."
                ),
            }
        ],
    }

# Combine the four research branches into a single report.
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

    decline_pct = (
        (production["target_units"] - production["actual_units"])
        / production["target_units"]
    ) * 100

    repair_count = sum(
        record["type"] == "repair"
        for record in maintenance["history"]
    )


    risk_factors = sum([
        equipment["temperature"] >= 85,
        incidents["recent_incidents"] >= 2,
        repair_count >= 3,
        decline_pct >= 10,
    ])

    if risk_factors >= 3:
        risk_level = "high"
    elif risk_factors >= 1:
        risk_level = "medium"
    else:
        risk_level = "low"


    report = InvestigationReport(
        machine_id=state["machine_id"],
        findings=findings,
        risk_level=risk_level,
        recommendation=(
            "Schedule a maintenance review of: "
            f"{maintenance['recurring_issue']}."
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
#--------------------------------------------
# EDGES & ROUTING
#--------------------------------------------
#NA

#--------------------------------------------
# GRAPH ASSEMBLY
#--------------------------------------------
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
builder.add_edge( # This creates a waiting edge.
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
#--------------------------------------------
# ENTRYPOINT
#--------------------------------------------
#NA