
from typing import TypedDict

'''
By inheriting from TypedDict, you are creating a blueprint that says: 
"Any dictionary representing an EquipmentRecord must contain exactly these 5 keys, and each key must hold this specific type of data."
'''
class EquipmentRecord(TypedDict):
    machine_id: str
    name: str
    department: str
    status: str
    temperature: float
    installation_year: int


# Simulated manufacturing equipment database
# str (The Key): This tells Python that the lookup keys will always be strings (text), like "M-103"
EQUIPMENT_DB: dict[str, EquipmentRecord] = { # EquipmentRecord (The Value): This tells Python that whatever is filed under that key will be a full record dictionary matching your EquipmentRecord blueprint.

    "M-103": {
        "machine_id": "M-103", # This makes it easy to retrieve a machine using its ID: machine = EQUIPMENT_DB["M-103"]
        "name": "CNC Milling Machine",
        "department": "Production Line 3",
        "status": "Maintenance Required",
        "temperature": 85.5,
        "installation_year": 2020
    },
    "M-104": {
        "machine_id": "M-104",
        "name": "Hydraulic Press",
        "department": "Production Line 1",
        "status": "Operational",
        "temperature": 62.3,
        "installation_year": 2018
    },
    "M-105": {
        "machine_id": "M-105",
        "name": "Industrial Conveyor",
        "department": "Production Line 2",
        "status": "Offline",
        "temperature": 25.0,
        "installation_year": 2019
    },
}



from pydantic import BaseModel, Field

class EquipmentInput(BaseModel): # Basemodel Creates a Pydantic model that validates input data at runtime.
    machine_id: str = Field( # Defines a required string field. Adds a description explaining what the field represents.
        description="The unique equipment ID, such as M-103."
    )
'''
When an LLM eventually uses this tool, it needs to understand what arguments to provide.
The tool schema tells the LLM that machine_id is required and should look like "M-103".
This is an important part of reliable tool calling.
'''

from langchain_core.tools import tool


@tool(args_schema=EquipmentInput)
def get_equipment_details(machine_id: str) -> dict:
    """Retrieve a machine's name, status, department, and temperature."""

    machine = EQUIPMENT_DB.get(machine_id)

    if machine is None:
        return {
            "outcome": "not_found",
            "machine_id": machine_id,
            "error": "Equipment record does not exist.",
        }

    return {
        "outcome": "success",
        **dict(machine), # This unpacks the machine dictionary into the return dictionary, effectively merging the two dictionaries. The ** operator takes each key-value pair from the machine dictionary and adds it to the new dictionary being returned.
    }



@tool(args_schema=EquipmentInput)
def get_maintenance_history(machine_id: str) -> dict:
    """Retrieve maintenance history for a manufacturing machine.

    Use this tool when the user asks about previous repairs,
    service history, or maintenance performed on equipment.
    """

    # Simulated maintenance records
    maintenance_db: dict[str, list[str]] = {
        "M-103": [
            "October 15: Cooling system inspected",
            "October 10: Temperature sensor replaced",
        ],
        "M-104": [
            "October 12: Hydraulic pressure checked",
        ],
        "M-105": [
            "October 18: Conveyor motor inspected",
        ],
    }

    # Return an error if the machine does not exist
    if machine_id not in EQUIPMENT_DB:
        return {"error": f"Machine {machine_id} not found"}

    # Return the machine's maintenance records
    return {
        "machine_id": machine_id,
        "maintenance_history": maintenance_db.get(machine_id, []),
    }
