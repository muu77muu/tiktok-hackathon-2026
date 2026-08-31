
# Catalog rows in Supabase store list-ish fields (categories, features,
# description) as stringified Python literals ("['Women', 'Dresses']") and
# price as text. Normalize them back to real types at the boundary so
# filtering.py's record_matches and the _product_text builders behave the
# same as they did over the original JSONL records (where these were lists).

import ast

LIST_FIELDS = ("categories", "features", "description")


def parse_list_field(value) -> list:
    if isinstance(value, list):
        return value
    if not value or not isinstance(value, str):
        return []
    try:
        parsed = ast.literal_eval(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except (ValueError, SyntaxError):
        return [value]  # plain prose field, keep as single item


def parse_price(value):
    if value is None or isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_record(record: dict) -> dict:
    out = dict(record)
    for field in LIST_FIELDS:
        if field in out:
            out[field] = parse_list_field(out[field])
    if "price" in out:
        out["price"] = parse_price(out["price"])
    return out
