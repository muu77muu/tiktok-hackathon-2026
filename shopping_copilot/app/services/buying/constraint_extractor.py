
# to extract purchasing constraints from a user's shopping request

from dataclasses import dataclass, field
from typing import Any

@dataclass
class PriceRange:
    min_price: float | None = None
    max_price: float | None = None
    currency: str = "USD"

@dataclass
class Constraints:
    """Structured representation of what the user is looking for."""

    category: str | None = None
    subcategory: str | None = None
    price: PriceRange = field(default_factory=PriceRange)
    brands_include: list[str] = field(default_factory=list)
    brands_exclude: list[str] = field(default_factory=list)
    attributes: dict[str, Any] = field(default_factory=dict)  # e.g. {"color": "black", "size": "M"}
    must_have: list[str] = field(default_factory=list)   # hard requirements, e.g. "waterproof"
    nice_to_have: list[str] = field(default_factory=list)  # soft preferences
    quantity: int = 1
    raw_query: str = ""
    confidence: float = 0.0  # extractor's confidence in this extraction
    ambiguous_fields: list[str] = field(default_factory=list)  # fields the extractor is unsure about

    def is_empty(self) -> bool:
        return not any(
            [
                self.category,
                self.brands_include,
                self.attributes,
                self.must_have,
                self.price.min_price,
                self.price.max_price,
            ]
        )


EXTRACTION_SCHEMA_HINT = """
Return a JSON object with this shape (omit fields you can't infer):
{
  "category": str | null,
  "subcategory": str | null,
  "price": {"min_price": number | null, "max_price": number | null, "currency": str},
  "brands_include": [str],
  "brands_exclude": [str],
  "attributes": {"<attribute_name>": "<value>"},
  "must_have": [str],
  "nice_to_have": [str],
  "quantity": int,
  "confidence": number,       // 0.0-1.0, how confident you are in this extraction
  "ambiguous_fields": [str]   // field names you're unsure about, e.g. ["price", "category"]
}
"""


class ConstraintExtractor:
    def __init__(self, llm_client=None, prompt_template: str | None = None):
        """
        llm_client: object exposing `.complete(system: str, user: str) -> str` (raw JSON text)
        prompt_template: system prompt for extraction; falls back to a default if not provided.
        """
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()

    def _default_prompt(self) -> str:
        return (
            "You extract structured shopping constraints from a user's message. "
            "Only include fields you can infer with reasonable confidence; "
            "leave others null or empty. Do not invent brands, prices, or attributes "
            "that aren't stated or clearly implied.\n\n" + EXTRACTION_SCHEMA_HINT
        )

    async def extract(self, query: str, context: dict | None = None) -> Constraints:
        context = context or {}
        prior_constraints: Constraints | None = context.get("prior_constraints")

        user_prompt = self._build_user_prompt(query, prior_constraints)
        raw = await self.llm_client.complete(
            system=self.prompt_template, user=user_prompt
        )
        parsed = self._parse_response(raw)

        constraints = self._to_constraints(parsed, raw_query=query)

        # Merge with prior turn's constraints so a follow-up like
        # "actually under $50" refines rather than replaces context.
        if prior_constraints:
            constraints = self._merge(prior_constraints, constraints)

        return constraints

    def _build_user_prompt(self, query: str, prior: Constraints | None) -> str:
        if prior and not prior.is_empty():
            return (
                f"Previous known constraints: {prior.__dict__}\n"
                f"New message: {query}\n"
                "Update or add to the constraints based on the new message."
            )
        return f"Message: {query}"

    def _parse_response(self, raw: str) -> dict:
        import json

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return {}

    def _to_constraints(self, parsed: dict, raw_query: str) -> Constraints:
        price_data = parsed.get("price") or {}
        return Constraints(
            category=parsed.get("category"),
            subcategory=parsed.get("subcategory"),
            price=PriceRange(
                min_price=price_data.get("min_price"),
                max_price=price_data.get("max_price"),
                currency=price_data.get("currency", "USD"),
            ),
            brands_include=parsed.get("brands_include", []) or [],
            brands_exclude=parsed.get("brands_exclude", []) or [],
            attributes=parsed.get("attributes", {}) or {},
            must_have=parsed.get("must_have", []) or [],
            nice_to_have=parsed.get("nice_to_have", []) or [],
            quantity=parsed.get("quantity", 1) or 1,
            raw_query=raw_query,
            confidence=parsed.get("confidence", 0.0) or 0.0,
            ambiguous_fields=parsed.get("ambiguous_fields", []) or [],
        )

    def _merge(self, prior: Constraints, new: Constraints) -> Constraints:
        """New, explicitly-stated fields override prior ones; unset new
        fields fall back to prior values."""
        merged = Constraints(**prior.__dict__)
        for f in (
            "category",
            "subcategory",
            "quantity",
        ):
            new_val = getattr(new, f)
            if new_val:
                setattr(merged, f, new_val)

        if new.price.min_price is not None or new.price.max_price is not None:
            merged.price = new.price

        merged.brands_include = new.brands_include or merged.brands_include
        merged.brands_exclude = list(set(merged.brands_exclude) | set(new.brands_exclude))
        merged.attributes = {**merged.attributes, **new.attributes}
        merged.must_have = list(set(merged.must_have) | set(new.must_have))
        merged.nice_to_have = list(set(merged.nice_to_have) | set(new.nice_to_have))
        merged.raw_query = new.raw_query
        merged.confidence = new.confidence
        merged.ambiguous_fields = new.ambiguous_fields
        return merged