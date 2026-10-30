
from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END

#Define the Equipment Agent's state
class EquipmentState(TypedDict):
    machine_id: str

    equipment_data: NotRequired[dict]
    maintenance_required: NotRequired[bool]
    equipment_summary: NotRequired[str]


EQUIPMENT_DB = {
    "M-103": {
        "machine_id": "M-103",
        "name": "CNC Milling Machine",
        "status": "Maintenance Required",
        "temperature": 85.5,
    },
    "M-104": {
        "machine_id": "M-104",
        "name": "Hydraulic Press",
        "status": "Operational",
        "temperature": 62.3,
    },
    "M-105": {
        "machine_id": "M-105",
        "name": "Industrial Conveyor",
        "status": "Offline",
        "temperature": 25.0,
    },
}

# Create the equipment lookup node
def lookup_equipment(state: EquipmentState) -> dict:
    machine_id = state["machine_id"]

    equipment = EQUIPMENT_DB.get(machine_id)

    if equipment is None:
        return {
            "equipment_data": {
                "machine_id": machine_id,
                "status": "Not Found",
            }
        }

    return {
        "equipment_data": dict(equipment)
    }

# Create the equipment assessment node
def assess_equipment(state: EquipmentState) -> dict:
    equipment = state["equipment_data"]

    status = equipment["status"]

    maintenance_required = status in {
        "Maintenance Required",
        "Offline",
    }

    return {
        "maintenance_required": maintenance_required
    }

# Create the summary node
def summarize_equipment(state: EquipmentState) -> dict:
    equipment = state["equipment_data"]

    machine_id = state["machine_id"]
    status = equipment["status"]

    if status == "Not Found":
        summary = (
            f"Machine {machine_id} was not found."
        )

    elif state["maintenance_required"]:
        summary = (
            f"Machine {machine_id} has status '{status}' "
            "and requires maintenance review."
        )

    else:
        summary = (
            f"Machine {machine_id} is operational."
        )

    return {
        "equipment_summary": summary
    }

# Compile the Equipment Agent

builder = StateGraph(EquipmentState)

builder.add_node("lookup", lookup_equipment)
builder.add_node("assess", assess_equipment)
builder.add_node("summarize", summarize_equipment)

builder.add_edge(START, "lookup")
builder.add_edge("lookup", "assess")
builder.add_edge("assess", "summarize")
builder.add_edge("summarize", END)

equipment_graph = builder.compile()
