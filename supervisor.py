#--------------------------------------------
# IMPORTS & CONFIGURATION
#--------------------------------------------
from request_validation import ask_for_clarification, classify_intent, prepare_action, resolve_clarification, route_after_clarification, route_intent, run_equipment_agent, run_investigation_agent, run_maintenance_action, validate_request
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

#--------------------------------------------
# STATE
#--------------------------------------------
from state import State
#--------------------------------------------
# TOOLS 
#--------------------------------------------
#NA

#--------------------------------------------
# NODES
#--------------------------------------------

# This node composes a final response based on the results from the agents.
def compose_response(state: State) -> dict:
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


#--------------------------------------------
# EDGES & ROUTING
#--------------------------------------------
#NA


#--------------------------------------------
# GRAPH ASSEMBLY
#--------------------------------------------



builder = StateGraph(State)


builder.add_node("classify_intent", classify_intent)
builder.add_node("validate_request", validate_request)
builder.add_node("equipment_agent", run_equipment_agent)
builder.add_node("investigation_agent", run_investigation_agent)
builder.add_node("prepare_action", prepare_action)
builder.add_node("maintenance_action", run_maintenance_action)
builder.add_node("ask_for_clarification", ask_for_clarification)
builder.add_node("compose_response", compose_response)
builder.add_node("resolve_clarification", resolve_clarification)

# Start by checking for an unfinished request.
builder.add_edge(START, "resolve_clarification")

# If the user completed a pending request, skip classification.
# Otherwise, classify the new request normally.
builder.add_conditional_edges(
    "resolve_clarification",
    route_after_clarification,
    {
        "resolved": "validate_request",
        "new_request": "classify_intent",
    },
)

# Classify a new request, then validate it.
builder.add_edge("classify_intent", "validate_request")

# Route the validated request.
builder.add_conditional_edges(
    "validate_request",      # 1. STARTING POINT: When the "validate_request" node finishes running...
    route_intent,    # 2. THE DECISION MAKER: Run this Python function to figure out the user's goal...
    {                # 3. THE MAP: Based on what that function says, go to one of these destinations:
        "equipment_agent": "equipment_agent",
        "investigation_agent": "investigation_agent",
        "maintenance_action": "prepare_action",
        "clarify": "ask_for_clarification",
    },
)

# Maintenance action workflow.
builder.add_edge("prepare_action", "maintenance_action")

# Specialized agents return to the Supervisor response node.
builder.add_edge("equipment_agent", "compose_response")
builder.add_edge("investigation_agent", "compose_response")
builder.add_edge("maintenance_action", "compose_response")

# Clarification returns a question to the user.
builder.add_edge("ask_for_clarification", END)

# Completed requests end after composing a response.
builder.add_edge("compose_response", END)


graph = builder.compile(
    checkpointer=InMemorySaver()
)


#--------------------------------------------
# ENTRYPOINT
#--------------------------------------------

