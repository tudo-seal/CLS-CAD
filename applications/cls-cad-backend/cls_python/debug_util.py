from collections.abc import Iterable


def deep_str(obj) -> str:
    sep = ",\n"
    if isinstance(obj, list):
        return f"[{sep.join(map(deep_str, obj))}]"
    elif isinstance(obj, dict):
        return f"map([{sep.join(map(lambda kv: ':'.join([deep_str(kv[0]), deep_str(kv[1])]) , obj.items()))}])"
    elif isinstance(obj, set):
        return f"set([{sep.join(map(deep_str, obj))}])"
    elif isinstance(obj, tuple):
        return f"({sep.join(map(deep_str, obj))})"
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, Iterable):
        return f"iter([{sep.join(map(deep_str, obj))}])"
    else:
        return str(obj)
