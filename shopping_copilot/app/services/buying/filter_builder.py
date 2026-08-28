
# to convert validated shopping constraints into structured catalog filters

class FilterBuilder:
    def build(self, constraints: dict) -> dict:
        
        return {
            "category": constraints.get("category"),
            "price_min": constraints.get("price", {}).get("min"),
            "price_max": constraints.get("price", {}).get("max"),
            "brands": constraints.get("brands", []),
            "attributes": constraints.get("attributes", {}),
        }