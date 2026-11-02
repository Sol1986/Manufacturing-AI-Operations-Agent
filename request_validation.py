#--------------------------------------------
# IMPORTS & CONFIGURATION
#--------------------------------------------
import re
import uuid

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from schemas import IntentClassification, ClarificationAnswer

from agents.equipment_agent import equipment_graph
from agents.investigation_agent import investigation_graph
from agents.maintenance_action import maintenance_action_graph



load_dotenv()

llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

#--------------------------------------------
# STATE
#--------------------------------------------

from state import State


#--------------------------------------------
# Node
#--------------------------------------------

# This node checks whether the user is answering a previous question.
def resolve_clarification(state: State) -> dict:
    pending = state.get("pending_request")

    if not pending:
        return {"clarification_resolved": False}

    # The first message was too vague to classify, so classify it again with the reply.
    if pending["intent"] == "clarify":
        return {
            "user_request": f"{pending['user_request']}\nFollow-up: {state['user_request']}",
            "pending_request": None,
            "clarification_resolved": False,
        }


    instructions = SystemMessage(
        content=(
            "You are checking a user's reply to a clarifying "
            "question from OpsPilot, a manufacturing operations "
            "assistant.\n\n"
            f"Pending task: {pending['intent']}\n"
            f"Information requested: {pending['missing_fields']}\n\n"
            "Set answers_question to false if the reply is a new "
            "or unrelated request. "
            "Extract only values explicitly provided. "
            "Never invent missing information."
        )
    )

    extractor = llm.with_structured_output(ClarificationAnswer)

    answer = extractor.invoke(
        [
            instructions,
            HumanMessage(content=state["user_request"]),
        ]
    )

    # The user moved on, so drop the old task and treat this as a new request.
    if not answer.answers_question:
        return {
            "pending_request": None,
            "clarification_resolved": False,
        }

    machine_id = pending.get("machine_id")

    if not machine_id and answer.machine_id:
        candidate = answer.machine_id.strip().upper()

        if re.fullmatch(r"M-\d+", candidate):
            machine_id = candidate

    return {
        "intent": pending["intent"],
        "issue": pending.get("issue") or answer.issue,
        "machine_id": machine_id,
        "pending_request": None,
        "clarification_resolved": True,
        "priority": pending.get("priority"),
        "missing_fields": [],
        "user_request": pending["user_request"],

    }


# This node checks whether the user is answering a previous question.
def route_after_clarification(state: State) -> str:
    if state.get("clarification_resolved"):
        return "resolved"

    return "new_request"

# This node classifies the intent of the user request.
def classify_intent(state: State) -> dict:

    last_machine_id = state.get("machine_id") or state.get("last_machine_id")

    instructions = SystemMessage(
        content=(
            "You are the intent classifier for OpsPilot, "
            "a manufacturing operations assistant.\n\n"
            "Classify the request into exactly one category:\n"
            "- equipment: equipment status, details, "
            "maintenance history, or information lookup.\n"
            "- investigation: causes, trends, recurring "
            "problems, incidents, or production analysis.\n"
            "- action: explicit requests to create or "
            "modify a maintenance work order.\n"
            "- clarify: ambiguous or unsupported requests.\n\n"
            "Extract only machine IDs explicitly provided. "
            "Never invent missing information. "
            "Do not classify an information lookup as an "
            "action merely because it mentions maintenance.\n\n"
            f"Most recently discussed machine: {last_machine_id or 'none'}. "
            "Use it as machine_id only when the request clearly "
            "refers back to it, such as 'it' or 'that machine'."

        )
    )

    classifier = llm.with_structured_output(
    IntentClassification
)

    response = classifier.invoke(
        [
            instructions,
            HumanMessage(content=state["user_request"]),
        ]
    )

    return {
        "intent": response.intent,
        "machine_id": response.machine_id,
        "issue": response.issue,
        "priority": response.priority,
        "last_machine_id": response.machine_id or last_machine_id,
    }

# This node validates the classified intent and machine ID.
def validate_request(state: State) -> dict:
    intent = state["intent"]
    missing = []

    if intent == "clarify":
        missing.append("what the user wants to do")
    else:
        if not state.get("machine_id"):
            missing.append("machine_id")
        if intent == "action" and not state.get("issue"):
            missing.append("issue")

    return {"missing_fields": missing}



# This node routes the request to the appropriate agent based on the intent.
def route_intent(state: State) -> str:
    
    if state.get("missing_fields"):
        return "clarify"

    intent = state["intent"]

    if intent == "equipment":
        return "equipment_agent"

    if intent == "investigation":
        return "investigation_agent"

    if intent == "action":
        return "maintenance_action"

    return "clarify"

# This node generates a clarifying question for the user.
def ask_for_clarification(state: State) -> dict:
    missing_fields = state["missing_fields"]

    response = llm.invoke(
        f"""
        You are OpsPilot, a manufacturing operations assistant.

        Original request: {state["user_request"]}
        Intended task: {state["intent"]}
        Missing information: {missing_fields}

        Ask one concise, specific question that obtains
        the missing information needed to continue.

        Do not guess missing values.
        Do not execute the user's request.
        """
    )

    intent = state["intent"]

    return {
        "pending_request": {
            "intent": intent,
            "machine_id": state.get("machine_id"),
            "issue": state.get("issue"),
            "priority": state.get("priority"),
            "missing_fields": missing_fields,
            "user_request": state["user_request"],

        },
        "final_response": response.content,
    }

# This node runs the equipment agent to retrieve information about a machine.
def run_equipment_agent(state: State) -> dict:

    result = equipment_graph.invoke(
        {
            "machine_id": state["machine_id"],
            "user_request": state["user_request"],
        }
    )

    return {
        "agent_result": {
            "agent": "equipment",
            "summary": result["equipment_summary"],
        }
    }

# This node runs the investigation agent to analyze issues and trends related to a machine.
async def run_investigation_agent(
    state: State,
) -> dict:
    result = await investigation_graph.ainvoke(
        {
            "machine_id": state["machine_id"],
            "findings": [],
        }
    )

    return {
        "agent_result": {
            "agent": "investigation",
            "report": result["investigation_report"],
        }
    }

# This node prepares the request for the maintenance action agent.
def prepare_action(state: State) -> dict:
    return {
        "request_id": str(uuid.uuid4()),
        "priority": state.get("priority") or "medium",
    }


# This node runs the maintenance action agent to create or modify a maintenance work order.
def run_maintenance_action(
    state: State,
) -> dict:
    result = maintenance_action_graph.invoke(
        {
            "request_id": state["request_id"],
            "machine_id": state["machine_id"],
            "issue": state["issue"],
            "priority": state["priority"],
        }
    )

    return {
        "agent_result": {
            "agent": "action",
            "result": result["final_result"],
        }
    }

