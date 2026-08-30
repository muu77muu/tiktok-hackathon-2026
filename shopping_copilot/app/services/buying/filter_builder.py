
# to convert validated shopping constraints into structured catalog filters

"""
Translates a validated Constraints object into the filter dict shape your
retrieval layer (metadata_filter.py / category_retriever.py) expects.
This is the one place that knows about retrieval-layer filter syntax, so if
that syntax changes, only this file needs to change.
"""

from __future__ import annotations

from .constraint_extractor import Constraints

class FilterBuilder:
    def __init__(self, attribute_field_map: dict[str, str] | None = None):
        """
        attribute_field_map: optional mapping from Constraints.attributes
        keys (e.g. "color") to the actual indexed field name (e.g.
        "product.color_normalized"), in case they differ.
        """
        self.attribute_field_map = attribute_field_map or {}

    async def build(self, constraints: Constraints) -> dict:
        filters: dict = {"must": [], "should": [], "must_not": []}

        if constraints.category:
            filters["must"].append({"field": "category", "op": "eq", "value": constraints.category})

        if constraints.subcategory:
            filters["must"].append(
                {"field": "subcategory", "op": "eq", "value": constraints.subcategory}
            )

        price_filter = self._build_price_filter(constraints)
        if price_filter:
            filters["must"].append(price_filter)

        if constraints.brands_include:
            filters["must"].append(
                {"field": "brand", "op": "in", "value": constraints.brands_include}
            )

        if constraints.brands_exclude:
            filters["must_not"].append(
                {"field": "brand", "op": "in", "value": constraints.brands_exclude}
            )

        for attr_name, attr_value in constraints.attributes.items():
            field_name = self.attribute_field_map.get(attr_name, f"attributes.{attr_name}")
            filters["must"].append({"field": field_name, "op": "eq", "value": attr_value})

        for req in constraints.must_have:
            filters["must"].append({"field": "tags", "op": "contains", "value": req})

        # rather than the retrieval layer excluding candidates that lack them
        for pref in constraints.nice_to_have:
            filters["should"].append({"field": "tags", "op": "contains", "value": pref})

        return self._clean(filters)

    def _build_price_filter(self, constraints: Constraints) -> dict | None:
        lo, hi = constraints.price.min_price, constraints.price.max_price
        if lo is None and hi is None:
            return None
        range_value: dict = {}
        if lo is not None:
            range_value["gte"] = lo
        if hi is not None:
            range_value["lte"] = hi
        return {"field": "price", "op": "range", "value": range_value}

    def _clean(self, filters: dict) -> dict:
        """Drop empty clause lists so downstream code doesn't need to
        special-case empty must/should/must_not arrays."""
        return {k: v for k, v in filters.items() if v}