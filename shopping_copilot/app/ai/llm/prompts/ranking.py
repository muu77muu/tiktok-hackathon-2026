
# to build a product-ranking prompt for an LLM

def build_ranking_prompt(
    query: str,
    candidates: list[dict],
    context: dict | None = None,
) -> str:

    context = context or {}

    return f"""
Rank the following products according to their relevance
to the user's shopping request.

User request:
{query}

Shopping context:
{context}

Candidate products:
{candidates}

Prioritize:

1. Explicit user requirements
2. Product-category relevance
3. Attribute compatibility
4. Contextual relevance
5. User preferences

Do not introduce requirements that the user did not state.
""".strip()