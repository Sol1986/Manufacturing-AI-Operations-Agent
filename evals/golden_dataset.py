
GOLDEN_DATASET = [
    {
        "input": "What's the status of M-103?",
        "expected_intent": "equipment",
    },
    {
        "input": "Show maintenance history for M-104.",
        "expected_intent": "equipment",
    },
    {
        "input": "Why does M-103 keep overheating?",
        "expected_intent": "investigation",
    },
    {
        "input": "Investigate production losses on M-105.",
        "expected_intent": "investigation",
    },
    {
        "input": (
            "Create a work order for M-103 "
            "to inspect the cooling system."
        ),
        "expected_intent": "action",
    },
    {
        "input": "Check the machine.",
        "expected_intent": "clarify",
    },
]

'''
This is our initial golden dataset.

Each example contains:
- A user request.
- The expected intent.
For production, we'd expand this with paraphrases, ambiguous requests, missing machine IDs, unsupported actions, and adversarial inputs.

We should also include examples where the user mentions an action without requesting one.

For example:
Why was a work order created for M-103?

That's an information request, not authorization to create another work order.
'''

'''
For action routing, two especially useful metrics are:

- Precision: Of requests classified as actions, how many actually requested an action?
- Recall: Of actual action requests, how many did the classifier identify?

For potentially consequential actions, we generally want high precision, strong deterministic validation, and mandatory authorization before any side effect.
'''