
# to validate purchasing constraints before passing to retrieval layer
# distinguishes two failure modes that the pipeline treats very differently:
#   - "missing/ambiguous info"  -> ask the user (needs_clarification)
#   - "internally inconsistent" -> hard stop, explain why (validation error)

from dataclasses import dataclass, field

from .constraint_extractor import Constraints

# Categories that are unusable without at least one of these being present.
MIN_SIGNAL_FIELDS = ("category", "brands_include", "attributes", "must_have")

@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    clarification_prompt: str | None = None
    clarification_fields: list[str] = field(default_factory=list)


class ConstraintValidator:
    def __init__(self, min_confidence: float = 0.35):
        self.min_confidence = min_confidence

    async def validate(self, constraints: Constraints) -> ValidationResult:
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Hard consistency checks (never askable, always an error)
        price_error = self._check_price_range(constraints)
        if price_error:
            errors.append(price_error)

        brand_conflict = self._check_brand_conflict(constraints)
        if brand_conflict:
            errors.append(brand_conflict)

        if errors:
            return ValidationResult(is_valid=False, errors=errors)
        
        # Insufficient signal -> ask for clarification, not an error
        if constraints.is_empty():
            return ValidationResult(
                is_valid=False,
                clarification_prompt=("What are you shopping for? A category, brand, or a few must-have features would help me narrow it down."),
                clarification_fields=["category"],
            )

        if constraints.confidence and constraints.confidence < self.min_confidence:
            warnings.append(
                f"low_extraction_confidence({constraints.confidence:.2f})"
            )

        if constraints.ambiguous_fields:
            prompt = self._build_clarification_prompt(constraints.ambiguous_fields)
            return ValidationResult(
                is_valid=False,
                warnings=warnings,
                clarification_prompt=prompt,
                clarification_fields=constraints.ambiguous_fields,
            )

        return ValidationResult(is_valid=True, warnings=warnings)

    def _check_price_range(self, c: Constraints) -> str | None:
        lo, hi = c.price.min_price, c.price.max_price
        if lo is not None and hi is not None and lo > hi:
            return f"price_range_invalid: min({lo}) > max({hi})"
        if lo is not None and lo < 0:
            return "price_range_invalid: negative min_price"
        return None

    def _check_brand_conflict(self, c: Constraints) -> str | None:
        overlap = set(b.lower() for b in c.brands_include) & set(
            b.lower() for b in c.brands_exclude
        )
        if overlap:
            return f"brand_conflict: {sorted(overlap)} both included and excluded"
        return None

    def _build_clarification_prompt(self, fields: list[str]) -> str:
        field_prompts = {
            "price": "What's your budget?",
            "category": "What kind of product are you looking for?",
            "attributes": "Any specific features or specs you need?",
            "brands_include": "Any brand preference, or open to anything?",
        }
        questions = [field_prompts.get(f, f"Can you clarify {f}?") for f in fields]
        return " ".join(questions)