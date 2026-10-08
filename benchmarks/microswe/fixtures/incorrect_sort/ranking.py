def rank(records: list[dict]) -> list[dict]:
    return sorted(records, key=lambda item: (item["score"], item["name"]))
