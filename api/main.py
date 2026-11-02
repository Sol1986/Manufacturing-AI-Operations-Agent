
from uuid import uuid4
import logging
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
from agents.maintenance_action import ApprovalDecision, WorkOrderChanges
from langgraph.types import Command
from supervisor import graph

# Build the FastAPI application
app = FastAPI(
    title="OpsPilot API",
    description="Manufacturing Operations AI Agent",
    version="1.0.0",
)

logger = logging.getLogger("uvicorn.error")


# Define the request schemas
class OpsPilotRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
    )


class ApprovalRequest(BaseModel):
    action: Literal[
        "approve",
        "reject",
        "edit",
    ]

    changes: WorkOrderChanges | None = None


# Build a helper for formatting graph results
def format_graph_result(thread_id: str, result: dict) -> dict:
    interrupts = result.get("__interrupt__", ())

    if interrupts:
        interrupt_payload = interrupts[0].value

        return {
            "thread_id": thread_id,
            "status": "awaiting_approval",
            "interrupt": interrupt_payload,
        }

    return {
        "thread_id": thread_id,
        "status": "completed",
        "response": result.get("final_response"),
    }

# Log why a request failed validation, not just the 422 status
@app.exception_handler(RequestValidationError)
async def log_validation_error(request: Request, exc: RequestValidationError):
    logger.warning(
        "422 on %s: %s",
        request.url.path,
        exc.errors(),
    )
    return await request_validation_exception_handler(request, exc)
    
# Create the request endpoint
@app.post("/requests")
async def create_request(request: OpsPilotRequest):
    thread_id = str(uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    result = await graph.ainvoke(
        {
            "user_request": request.message,
        },
        config=config,
    )

    return format_graph_result(
        thread_id,
        result,
    )


import json

from fastapi.responses import StreamingResponse

# Add streaming to the API
@app.post("/requests/stream")
async def stream_request(request: OpsPilotRequest):
    thread_id = str(uuid4())

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    async def generate():
        async for update in graph.astream(
            {"user_request": request.message},
            config=config,
            stream_mode="updates",
        ):
            yield (
                f"data: {json.dumps(update, default=str)}\n\n"
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


# Create the approval endpoint
@app.post("/threads/{thread_id}/approvals")
async def submit_approval(
    thread_id: str,
    request: ApprovalRequest,
):
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    snapshot = graph.get_state(config)

    if not snapshot.tasks:
        raise HTTPException(
            status_code=409,
            detail="No active workflow awaiting approval.",
        )

    pending_interrupts = [
        interrupt
        for task in snapshot.tasks
        for interrupt in task.interrupts
    ]

    if not pending_interrupts:
        raise HTTPException(
            status_code=409,
            detail="Workflow is not awaiting approval.",
        )

    # LOCAL DEMO ONLY.
    # Production: derive identity from authenticated claims.
    reviewer_id = "demo-supervisor"

    validated = ApprovalDecision.model_validate(
        {
            "action": request.action,
            "changes": request.changes,
            "reviewer_id": reviewer_id,
        }
    )

    result = await graph.ainvoke(
        Command(
            resume=validated.model_dump()
        ),
        config=config,
    )

    return format_graph_result(
        thread_id,
        result,
    )

# Send a follow-up message to an existing thread
@app.post("/threads/{thread_id}/messages")
async def add_message(thread_id: str, request: OpsPilotRequest):
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail="Thread not found.",
        )

    if any(task.interrupts for task in snapshot.tasks):
        raise HTTPException(
            status_code=409,
            detail="Workflow is awaiting approval.",
        )

    result = await graph.ainvoke(
        {"user_request": request.message},
        config=config,
    )

    return format_graph_result(
        thread_id,
        result,
    )


# Create the state inspection endpoint
@app.get("/threads/{thread_id}")
def get_thread_state(thread_id: str):
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail="Thread not found.",
        )

    return {
        "thread_id": thread_id,
        "state": snapshot.values,
        "next": list(snapshot.next),
    }

# Add a health endpoint
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "opspilot",
    }

