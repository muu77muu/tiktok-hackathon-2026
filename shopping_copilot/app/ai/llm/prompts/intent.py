
# to build a prompt for determining shopping intent from user requests

def build_intent_prompt(
    message: str,
    context: dict | None = None,
) -> str:

    context = context or {}

    return f"""
Determine the shopping intent for the following user request.

User request:
{message}

Relevant context:
{context}

Classify the request as one of:

- buying
- browsing
- unclear

Return only the classification and a concise rationale.
""".strip()