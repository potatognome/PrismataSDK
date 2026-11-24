def find_field(data, field):
    if field in data:
        return data[field]
    for key, value in data.items():
        if isinstance(value, dict) and field in value:
            return value[field]
    return None

def flatten_registry(registry):
    flat = {}
    for kind, entries in registry.items():
        for entry_id, info in entries.items():
            flat[entry_id] = info
    return flat
