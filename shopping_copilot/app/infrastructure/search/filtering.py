
# Shared by keyword_index.py, vector_index.py, and category_index.py so all indexes apply the same filters={"must": [{"field", "value", "op"}]} contract that retrieval_service.py's _extract_category builds and that metadata_filter.py presumably re-applies downstream.
# "category" is special-cased to match anywhere in a product's category chain, case-insensitively, since categories are a list, not a scalar.

def record_matches(record: dict, filters: dict | None) -> bool:
    if not filters:
        return True
    for clause in filters.get("must", []):
        field = clause.get("field")
        if field is None:
            continue
        value = clause.get("value")
        op = clause.get("op", "eq")

        if field == "category":
            chain = record.get("categories") or []
            terms = {str(c).casefold() for c in chain} if isinstance(chain, list) else set()
            if str(value).casefold() not in terms:
                return False
            continue

        record_value = record.get(field)
        if op == "eq" and record_value != value:
            return False
        if op == "ne" and record_value == value:
            return False
        if op == "gte" and (record_value is None or record_value < value):
            return False
        if op == "lte" and (record_value is None or record_value > value):
            return False
        if op == "in" and record_value not in (value or []):
            return False
        if op == "contains" and (not record_value or value not in record_value):
            return False
    return True

# product fields a downstream ranking needs
def to_metadata(record: dict) -> dict:
    return {
        "title": record.get("title"),
        "price": record.get("price"),
        "categories": record.get("categories"),
        "average_rating": record.get("average_rating"),
        "rating_number": record.get("rating_number"),
        "store": record.get("store"),
    }