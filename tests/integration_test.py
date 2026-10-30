
import asyncio

from supervisor import graph


async def test_investigation():
    config = {
        "configurable": {
            "thread_id": "integration-investigation-001"
        }
    }

    result = await graph.ainvoke(
        {
            "user_request": (
                "Investigate why M-103 keeps overheating."
            )
        },
        config=config,
    )

    assert result["intent"] == "investigation"

    report = result["agent_result"]["report"]

    assert report["machine_id"] == "M-103"
    assert len(report["findings"]) == 4


if __name__ == "__main__":
    asyncio.run(test_investigation())

# This test calls the real LLM classifier, so it needs an API key and may incur usage costs. It also depends on the simulated data from Lesson 19.