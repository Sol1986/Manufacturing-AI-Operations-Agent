
from langchain_core.tools import tool
from schemas import EquipmentInput
from tools.equipment_db import EQUIPMENT_DB, MAINTENANCE_DB

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

     # Return an error if the machine does not exist
    if machine_id not in EQUIPMENT_DB:
        return {"error": f"Machine {machine_id} not found"}

    maintenance = MAINTENANCE_DB[machine_id]

    # Return the machine's maintenance records
    return {
        "machine_id": machine_id,
        "recurring_issue": maintenance["recurring_issue"],
        "maintenance_history": maintenance["history"],
    }
