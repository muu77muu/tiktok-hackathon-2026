
# to convert ranked product candidates into recommendation results suitable for the conversational layer

DEFAULT_DISPLAY_COUNT = 5

INTRO_SCHEMA_HINT = """
Return JSON: {"message": str}
Write one short, natural sentence introducing these results to the user.
Reference their stated need if relevant. Do not describe the products
individually -- that's handled separately.
"""

class RecommendationService:
    def __init__(
        self,
        llm_client=None,
        prompt_template: str | None = None,
        display_count: int = DEFAULT_DISPLAY_COUNT,
    ):
        self.llm_client = llm_client
        self.prompt_template = prompt_template or self._default_prompt()
        self.display_count = display_count

    def _default_prompt(self) -> str:
        return (
            "You introduce shopping search results to a user in one short, "
            "warm sentence.\n\n" + INTRO_SCHEMA_HINT
        )

    async def present(self, pipeline_result: dict, context: dict) -> dict:
        status = pipeline_result.get("status")

        if status == "no_results":
            return self._no_results_response(pipeline_result)
        if status == "error":
            return self._error_response(pipeline_result)
        if status == "needs_clarification":
            # shouldnt normally reach here; orchestration_service.py should route this to clarification_service before calling present()
            return {
                "status": "needs_clarification",
                "message": pipeline_result.get("clarification_prompt"),
                "products": [],
            }

        products = pipeline_result.get("ranked_products", [])[: self.display_count]
        intro = await self._build_intro(pipeline_result, context, products)

        return {
            "status": "ok",
            "message": intro,
            "products": [self._to_display_product(p) for p in products],
        }

    async def _build_intro(self, pipeline_result: dict, context: dict, products: list[dict]) -> str:
        if self.llm_client is None or not products:
            count = len(products)
            return f"Here are {count} option{'s' if count != 1 else ''} that might work:"

        query = pipeline_result.get("query", "")
        try:
            raw = await self.llm_client.complete(
                system=self.prompt_template,
                user=f"Query: {query}\nNumber of results: {len(products)}",
            )
            return self._parse(raw)
        except Exception:
            return "Here are a few options that might work:"

    def _parse(self, raw: str) -> str:
        import json

        cleaned = raw.strip().strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        try:
            data = json.loads(cleaned)
            return data.get("message") or "Here are a few options that might work:"
        except json.JSONDecodeError:
            return "Here are a few options that might work:"

    def _to_display_product(self, product: dict) -> dict:
        metadata = product.get("metadata", {})
        return {
            "product_id": product.get("product_id"),
            "title": metadata.get("title"),
            "price": metadata.get("price"),
            "brand": metadata.get("brand"),
            "rating": metadata.get("rating"),
            "image_url": metadata.get("image_url"),
            "rationale": product.get("llm_rationale"),
        }

    def _no_results_response(self, pipeline_result: dict) -> dict:
        return {
            "status": "no_results",
            "message": (
                "I couldn't find anything matching that. Want to try "
                "loosening a constraint, like price or brand?"
            ),
            "products": [],
        }

    def _error_response(self, pipeline_result: dict) -> dict:
        return {
            "status": "error",
            "message": "Something went wrong on my end searching for that -- mind trying again?",
            "products": [],
        }