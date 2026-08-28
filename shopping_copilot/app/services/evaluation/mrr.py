
# to calculate MRR (Mean Reciprocal Rank) for evaluating retrieval and recommendation performance
# measures how high the purchased product ranks among the retrieved candidates, with higher ranks contributing more to the score

class MeanReciprocalRank:
    def calculate(
        self,
        purchased_product_id: str,
        ranked_products: list[str],
    ) -> float:

        try:
            rank = ranked_products.index(
                purchased_product_id
            ) + 1
        except ValueError:
            return 0.0

        return 1.0 / rank

    def calculate_sessions(
        self,
        purchased_product_ids: list[str],
        ranked_products: list[list[str]],
    ) -> float:

        if not purchased_product_ids:
            return 0.0

        reciprocal_ranks = [
            self.calculate(
                purchased_product_id,
                products,
            )
            for purchased_product_id, products
            in zip(
                purchased_product_ids,
                ranked_products,
            )
        ]

        return sum(reciprocal_ranks) / len(
            reciprocal_ranks
        )