import json

import ujson
from orjson import orjson


def postprocess(data: dict):
    try:
        propagate_part_counts_in_part_json(data, data["count"])
    except TypeError:
        data = data()
        propagate_part_counts_in_part_json(data, data["count"])
    remove_unused_keys_prom_part_json(data)
    return data


def propagate_part_counts_in_part_json(data: dict, multiplier: int):
    for k, v in data["connections"].items():
        v["count"] *= multiplier
        v["cost"] *= multiplier
        propagate_part_counts_in_part_json(v, v["count"])
    return data


def remove_unused_keys_prom_part_json(data: dict):
    data.pop("requiredJointOriginsInfo", None)
    for k, v in data["connections"].items():
        remove_unused_keys_prom_part_json(v)
    return data


def fast_json_to_string(content: dict):
    try:
        return orjson.dumps(content)
    except TypeError:
        try:
            return ujson.dumps(content, ensure_ascii=False).encode("utf-8")
        except OverflowError:
            return json.dumps(content, ensure_ascii=False).encode("utf-8")
