#--------------------------------------------
# IMPORTS & CONFIGURATION
#--------------------------------------------
from typing import Annotated, NotRequired, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AnyMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from tools.equipment_tools import get_equipment_details, get_maintenance_history

load_dotenv()

tools = [get_equipment_details, get_maintenance_history]

llm = ChatOpenAI(model="gpt-5-mini", temperature=0)

#--------------------------------------------
# STATE
#--------------------------------------------
class EquipmentState(TypedDict):
    machine_id: str
    user_request: str

    messages: Annotated[list[AnyMessage], add_messages]
    equipment_summary: NotRequired[str]

#--------------------------------------------
# NODES
#--------------------------------------------
# The LLM either requests a tool call or writes the final answer.
def call_model(state: EquipmentState) -> dict:
    instructions = SystemMessage(
        content=(
            "You are the equipment agent for OpsPilot, "
            "a manufacturing operations assistant.\n\n"
            f"The machine in question is {state['machine_id']}.\n"
            "Use your tools to look up the information you need. "
            "Answer only from tool results. "
            "If a tool reports that a record does not exist, say so."
        )
    )

    response = llm.bind_tools(tools).invoke(
        [
            instructions,
            HumanMessage(content=state["user_request"]),
            *state.get("messages", []),
        ]
    )

    return {"messages": [response]}


# Save the LLM's final answer where run_equipment_agent expects it.
def summarize_equipment(state: EquipmentState) -> dict:
    return {
        "equipment_summary": state["messages"][-1].content
    }

#--------------------------------------------
# GRAPH ASSEMBLY
#--------------------------------------------
builder = StateGraph(EquipmentState)

builder.add_node("call_model", call_model)
builder.add_node("tools", ToolNode(tools))
builder.add_node("summarize", summarize_equipment)

builder.add_edge(START, "call_model")

builder.add_conditional_edges(
    "call_model",
    tools_condition,
    {
        "tools": "tools",
        END: "summarize",
    },
)

builder.add_edge("tools", "call_model")
builder.add_edge("summarize", END)

equipment_graph = builder.compile()
