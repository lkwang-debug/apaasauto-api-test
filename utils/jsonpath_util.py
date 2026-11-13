import re


class JsonPathNotFound(Exception):
    pass


_PATH_PART_PATTERN = re.compile(r"([^\[\]]+)|\[(\d+)\]")


def _split_expression(expression):
    if not expression.startswith("$"):
        raise ValueError(f"Unsupported JSONPath: {expression}")
    if expression == "$":
        return []

    body = expression[2:] if expression.startswith("$.") else expression[1:]
    tokens = []
    for segment in body.split("."):
        if not segment:
            continue
        for name, index in _PATH_PART_PATTERN.findall(segment):
            if name:
                tokens.append(name)
            elif index:
                tokens.append(int(index))
    return tokens


def extract_json_path(data, expression):
    current = data
    for token in _split_expression(expression):
        try:
            if isinstance(token, int):
                current = current[token]
            else:
                current = current[token]
        except (KeyError, IndexError, TypeError) as exc:
            raise JsonPathNotFound(f"JSONPath not found: {expression}") from exc
    return current
