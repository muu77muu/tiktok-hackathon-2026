class BuyingStrategy:
    def should_clarify(self, validation_result: dict) -> bool:
        return bool(
            validation_result.get("missing")
            or validation_result.get("conflicts")
        )

    def should_retrieve(self, validation_result: dict) -> bool:
        return (
            validation_result.get("valid", False)
            and not self.should_clarify(validation_result)
        )