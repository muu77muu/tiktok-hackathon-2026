
# to extract structured shopping constraints, preferences, and product attributes from user requests

def build_extraction_prompt(
    message: str,
    context: dict | None = None,
) -> str:

    context = context or {}

    return f"""
Extract structured shopping information from the user request.

User request:
{message}

Existing context:
{context}

Identify, where present:

- product category
- brand
- price constraints
- required attributes
- preferred attributes
- excluded attributes
- usage scenario
- quantity
- other relevant constraints

Do not invent information that is not supported by
the conversation.
""".strip()