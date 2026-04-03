import re

VARIABLE_PATTERN = re.compile(r"\{\{(.*?)\}\}")

def resolve_value(value: str, ctx):
    if not isinstance(value, str):
        return value

    def replace(match):
        key = match.group(1).strip()
        return str(ctx.data.get(key, ""))
    
    return VARIABLE_PATTERN.sub(replace, value)
