EQUIPMENT_DB = {
    "M-103": {
        "machine_id": "M-103",
        "name": "CNC Milling Machine",
        "status": "Maintenance Required",
        "temperature": 85.5,
        "department": "Production Line 3",
        "installation_year": 2020
    },
    "M-104": {
        "machine_id": "M-104",
        "name": "Hydraulic Press",
        "status": "Operational",
        "temperature": 62.3,
        "department": "Production Line 1",
        "installation_year": 2018
    },
    "M-105": {
        "machine_id": "M-105",
        "name": "Industrial Conveyor",
        "status": "Offline",
        "temperature": 25.0,
        "department": "Production Line 2",
        "installation_year": 2019
    },
}

MAINTENANCE_DB = {
    "M-103": {
        "recurring_issue": "Cooling system",
        "history": [
            {"date": "2026-10-15", "type": "inspection", "description": "Cooling system inspected"},
            {"date": "2026-10-10", "type": "repair", "description": "Temperature sensor replaced"},
            {"date": "2026-09-28", "type": "repair", "description": "Cooling pump repaired"},
            {"date": "2026-09-12", "type": "repair", "description": "Coolant line repaired"},
        ],
    },
    "M-104": {
        "recurring_issue": None,
        "history": [
            {"date": "2026-10-12", "type": "inspection", "description": "Hydraulic pressure checked"},
        ],
    },
    "M-105": {
        "recurring_issue": None,
        "history": [
            {"date": "2026-10-18", "type": "inspection", "description": "Conveyor motor inspected"},
        ],
    },
}


PRODUCTION_DB = {
    "M-103": {
        "target_units": 1000,
        "actual_units": 820,
        "downtime_minutes": 95,
    },
    "M-104": {
        "target_units": 500,
        "actual_units": 500,
        "downtime_minutes": 0,
    },
    "M-105": {
        "target_units": 750,
        "actual_units": 0,
        "downtime_minutes": 480,
    },
}

INCIDENT_DB = {
    "M-103": {
        "recent_incidents": 2,
        "incident_type": "Overheating",
    },
    "M-104": {
        "recent_incidents": 0,
        "incident_type": None,
    },
    "M-105": {
        "recent_incidents": 0,
        "incident_type": None,
    },  
}   