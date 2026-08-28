
# to define decision-making rules specific to exploratory shopping scenarios

class BrowsingStrategy:

    # query expansion
    def should_expand_query(self, scenario: dict) -> bool:
        return True

    # multi-query generation
    def should_generate_multiple_queries(
        self,
        scenario: dict,
    ) -> bool:
        return True

    # HyDE support
    def should_use_hyde(
        self,
        query: str,
        scenario: dict,
    ) -> bool:
        return False

    # clarification
    def needs_clarification(
        self,
        scenario: dict,
    ) -> bool:
        return False