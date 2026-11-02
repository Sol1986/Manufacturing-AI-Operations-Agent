import asyncio
import uuid

from langgraph.types import Command

from supervisor import graph

# This is a simple example of how to use the OpsPilot graph in a local testing environment.
def ask_for_approval(interrupt_value: dict) -> dict:
    print("\nApproval needed:")
    print(interrupt_value["proposal"])

    action = input("approve / reject: ").strip().lower()

    return {"action": action, "reviewer_id": "local-tester"}

# The main function runs an interactive loop where the user can input queries, and the OpsPilot graph processes them. If the graph requires approval for any action, it will pause and ask the user for a decision before continuing.
async def main():
    # The same thread_id lets the graph remember earlier turns.
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    while True:
        query = input("\nYou: ").strip()

        if query.lower() in {"quit", "exit"}:
            break

        result = await graph.ainvoke({"user_request": query}, config)

        # The graph pauses here until a work order is approved or rejected.
        while "__interrupt__" in result:
            decision = ask_for_approval(result["__interrupt__"][0].value)
            result = await graph.ainvoke(Command(resume=decision), config)

        print(f"\nOpsPilot: {result['final_response']}")


if __name__ == "__main__":
    asyncio.run(main())
