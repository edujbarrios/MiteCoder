def chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[i:i + size] for i in range(0, len(values) - size, size)]
