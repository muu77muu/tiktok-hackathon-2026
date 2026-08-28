
# to apply deterministic catalog constraints to product candidates

class MetadataFilter:
    def apply(
        self,
        products: list[dict],
        filters: dict,
    ) -> list[dict]:

        return products