
# to generate proactive clarifications for a user's shopping request

def build_clarification_prompt(
    message: str,
    context: dict | None = None,
    reason: str | None = None,
) -> str:

    context = context or {}

    return f"""
Generate a concise clarification question to help narrow
the user's shopping request.

User request:
{message}

Current context:
{context}

Reason clarification is required:
{reason or "The request is too general."}

The question should help identify the most useful missing
shopping constraint or preference.

Prefer a small number of clear options when appropriate.
""".strip()