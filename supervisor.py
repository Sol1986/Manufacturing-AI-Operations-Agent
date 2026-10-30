
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)

from old.schemas import IntentClassification
from old.state import OpsPilotState
from agents.equipment_agent import equipment_graph



load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
)

classifier = llm.with_structured_output(
    IntentClassification
)


def classify_intent(state: OpsPilotState) -> dict:
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
            "action merely because it mentions maintenance."
        )
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
    }

# Let's create a validation node.
def validate_request(state: OpsPilotState) -> dict:
    intent = state["intent"]
    machine_id = state.get("machine_id")

    if intent == "clarify":
        return {
            "intent": "clarify",
        }

    if not machine_id:
        return {
            "intent": "clarify",
        }

    if intent == "action":
        issue = state.get("issue")

        if not issue:
            return {
                "intent": "clarify",
            }

    return {} # means this node isn't changing any state fields.

'''
Why validate after the LLM?
Because the LLM is responsible for interpretation, but our application is responsible for enforcing workflow requirements.

This separation is especially important for actions that have external side effects.
'''

# Create the routing function
def route_intent(state: OpsPilotState) -> str:
    intent = state["intent"]

    if intent == "equipment":
        return "equipment_agent"

    if intent == "investigation":
        return "investigation_agent"

    if intent == "action":
        return "maintenance_action"

    return "clarify"



# Create the Equipment Agent adapter
def run_equipment_agent(state: OpsPilotState) -> dict:
    result = equipment_graph.invoke(
        {
            "machine_id": state["machine_id"],
        }
    )

    return {
        "agent_result": {
            "agent": "equipment",
            "summary": result["equipment_summary"],
        }
    }

# Create the Investigation Agent adapter

from agents.investigation_agent import investigation_graph


async def run_investigation_agent(
    state: OpsPilotState,
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



import uuid


def prepare_action(state: OpsPilotState) -> dict:
    request_id = state.get("request_id")

    if not request_id:
        request_id = str(uuid.uuid4())

    priority = state.get("priority") or "medium"

    return {
        "request_id": request_id,
        "priority": priority,
    }


from agents.maintenance_action import maintenance_action_graph

# Create the Maintenance Action adapter
def run_maintenance_action(
    state: OpsPilotState,
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

'''
This adapter is different from the others because the child graph can pause.

When it reaches interrupt(), the parent execution will also pause.

The application must resume the same checkpointed parent thread using Command(resume=...).

The child graph then continues its approval workflow.

This is why the parent graph needs a checkpointer.
'''

# Create the clarification node
def ask_for_clarification(state: OpsPilotState) -> dict:
    if not state.get("machine_id"):
        message = (
            "Which machine would you like me to check? "
            "Please provide its machine ID."
        )

    elif state.get("intent") == "action" and not state.get("issue"):
        message = (
            "What maintenance issue should the work order address?"
        )

    else:
        message = (
            "Could you clarify what you want OpsPilot to do?"
        )

    return {
        "final_response": message
    }

# Create the final response composer
# Now we'll write one node that handles outputs from all three specialized agents.
def compose_response(state: OpsPilotState) -> dict:
    agent_result = state["agent_result"]

    agent = agent_result["agent"]

    if agent == "equipment":
        response = agent_result["summary"]

    elif agent == "investigation":
        report = agent_result["report"]

        findings = "\n".join(
            f"- {finding['detail']}"
            for finding in report["findings"]
        )

        response = (
            f"Investigation: {report['machine_id']}\n"
            f"Risk: {report['risk_level']}\n\n"
            f"Findings:\n{findings}\n\n"
            f"Recommendation:\n{report['recommendation']}"
        )

    elif agent == "action":
        result = agent_result["result"]

        if result["status"] == "created":
            response = (
                f"Work order {result['work_order_id']} "
                f"was created for {result['machine_id']}."
            )
        else:
            response = (
                f"Work order request {result['request_id']} "
                "was rejected."
            )

    else:
        response = "Unable to process the request."

    return {
        "final_response": response
    }


# Build the complete supervisor graph
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver


builder = StateGraph(OpsPilotState)


builder.add_node("classify", classify_intent)
builder.add_node("validate", validate_request)

builder.add_node("equipment_agent", run_equipment_agent)

builder.add_node("investigation_agent", run_investigation_agent)

builder.add_node("prepare_action", prepare_action)

builder.add_node("maintenance_action", run_maintenance_action)

builder.add_node(
    "clarify",
    ask_for_clarification,
)

builder.add_node(
    "compose_response",
    compose_response,
)


builder.add_edge(START, "classify")
builder.add_edge("classify", "validate")


builder.add_conditional_edges(
    "validate",      # 1. STARTING POINT: When the "validate" node finishes running...
    route_intent,    # 2. THE DECISION MAKER: Run this Python function to figure out the user's goal...
    {                # 3. THE MAP: Based on what that function says, go to one of these destinations:
        "equipment_agent": "equipment_agent",
        "investigation_agent": "investigation_agent",
        "maintenance_action": "prepare_action",
        "clarify": "clarify",
    },
)


builder.add_edge(
    "prepare_action",
    "maintenance_action",
)


builder.add_edge(
    "equipment_agent",
    "compose_response",
)

builder.add_edge(
    "investigation_agent",
    "compose_response",
)

builder.add_edge(
    "maintenance_action",
    "compose_response",
)


builder.add_edge("clarify", END)
builder.add_edge("compose_response", END)


graph = builder.compile(
    checkpointer=InMemorySaver()
)





# # Test the Equipment Agent route
# from supervisor import graph


# config = {
#     "configurable": {
#         "thread_id": "equipment-test-001"
#     }
# }


# result = graph.invoke(
#     {
#         "user_request": "What's the status of machine M-103?"
#     },
#     config=config,
# )


# print(result["final_response"])

# '''
# What if a request needs multiple agents?
# Consider:
# Check M-103, investigate its overheating problem, and create a maintenance work order if needed.

# This request contains several tasks.

# Our current classifier supports only one intent.

# It cannot fully represent this request.

# That's a limitation of today's design, not something we should hide.

# A more advanced supervisor would need to:
# 1. Decompose the request into tasks.
# 2. Determine dependencies.
# 3. Execute independent tasks in parallel.
# 4. Wait for required evidence.
# 5. Decide whether an action should be proposed.
# 6. Request human approval before execution.
# '''