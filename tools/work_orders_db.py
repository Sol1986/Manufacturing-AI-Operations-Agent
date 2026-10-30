
import json
import sqlite3
from pathlib import Path


DB_PATH = Path("opspilot_work_orders.sqlite")


def initialize_database() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS work_orders (
                request_id TEXT PRIMARY KEY,
                work_order_id TEXT NOT NULL UNIQUE,
                proposal_json TEXT NOT NULL,
                status TEXT NOT NULL
            )
            """
        )


def create_work_order(
    request_id: str,
    proposal: dict,
) -> dict:
    work_order_id = f"WO-{request_id}"

    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO work_orders (
                request_id,
                work_order_id,
                proposal_json,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                request_id,
                work_order_id,
                json.dumps(proposal, sort_keys=True),
                "created",
            ),
        )

        row = conn.execute(
            """
            SELECT
                work_order_id,
                proposal_json,
                status
            FROM work_orders
            WHERE request_id = ?
            """,
            (request_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError(
            "Work order was not found after insertion."
        )

    return {
        "request_id": request_id,
        "work_order_id": row[0],
        "proposal": json.loads(row[1]),
        "status": row[2],
    }
