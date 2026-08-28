
# to coordinate evaluation of retrieval and recommendation performance across coverage, precision, and efficiency

class EvaluationService:
    def __init__(
        self,
        hit_rate=None,
        mrr=None,
        top_k_hit=None,
        mttc=None,
    ):
        self.hit_rate = hit_rate
        self.mrr = mrr
        self.top_k_hit = top_k_hit
        self.mttc = mttc

    def evaluate_session(
        self,
        purchased_product_id: str,
        retrieval_results: list[list[str]],
        recommendation_results: list[list[str]],
        turn_count: int,
        k: int = 10,
    ) -> dict:
        """
        Evaluate a single shopping session.

        Metric implementations are connected incrementally.
        """

        return {
            "purchased_product_id": purchased_product_id,
            "turn_count": turn_count,
            "k": k,
            "coverage": {},
            "precision": {},
            "efficiency": {},
        }