
# to measure whether the purchased product appears within the final recommendation Top-K
# keep Top-K Hit separate from MRR as they answer different questions

class TopKHit:
    def calculate(
        self,
        purchased_product_id: str,
        ranked_products: list[str],
        k: int = 10,
    ) -> float:

        return float(
            purchased_product_id
            in ranked_products[:k]
        )

    def calculate_sessions(
        self,
        purchased_product_ids: list[str],
        ranked_products: list[list[str]],
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
                ranked_products,
            )
        )

        return hits / len(purchased_product_ids)