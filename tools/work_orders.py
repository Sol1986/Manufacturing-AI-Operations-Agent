# Create an idempotent work-order tool
WORK_ORDER_DB: dict[str, dict] = {}


def create_work_order(
    request_id: str,
    proposal: dict,
) -> dict:
    """Create a work order once per request ID."""

    work_order_id = f"WO-{request_id}"

    if work_order_id in WORK_ORDER_DB:
        return WORK_ORDER_DB[work_order_id]

    record = {
        "work_order_id": work_order_id,
        **proposal,
        "status": "created",
    }

    WORK_ORDER_DB[work_order_id] = record

    return record