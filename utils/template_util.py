import re


PLACEHOLDER_PATTERN = re.compile(r"\$\{([^{}]+)\}")


class TemplateResolver:
    def __init__(self, config, variable_store):
        self.config = config
        self.variable_store = variable_store

    def resolve(self, value):
        if isinstance(value, dict):
            return {key: self.resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, str):
            full_match = PLACEHOLDER_PATTERN.fullmatch(value)
            if full_match:
                return self._lookup(full_match.group(1))
            return PLACEHOLDER_PATTERN.sub(lambda match: str(self._lookup(match.group(1))), value)
        return value

    def _lookup(self, name):
        if self.variable_store.contains(name):
            return self.variable_store.get(name)

        config_value = self.config.get_by_key(name, fallback=None)
        if config_value is not None:
            return config_value

        raise KeyError(f"Variable '{name}' is not defined")
