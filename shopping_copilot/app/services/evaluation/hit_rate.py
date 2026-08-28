
# to calculate hit rate at K for evaluating retrieval and recommendation performance

class HitRateAtK:
    def calculate(
        self,
        purchased_product_id: str,
        retrieved_products: list[str],
        k: int = 10,
    ) -> float:

        top_k = retrieved_products[:k]

        return float(
            purchased_product_id in top_k
        )

    def calculate_sessions(
        self,
        purchased_product_ids: list[str],
        retrieved_products: list[list[str]],
        k: int = 10,
    ) -> float:

        if not purchased_product_ids:
            return 0.0

        hits = sum(
            self.calculate(
                purchased_product_id,
                products,
                k,
            )
            for purchased_product_id, products
            in zip(
                purchased_product_ids,
                retrieved_products,
            )
        )

        return hits / len(purchased_product_ids)