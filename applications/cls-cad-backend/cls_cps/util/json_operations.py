import json
import re
from collections import defaultdict

import ujson
from orjson import orjson

from cls_cps.repository_builder import Part

part_counts: defaultdict = defaultdict(lambda: {"count": 0, "name": "", "cost": 0})
total_count, total_cost = 0, 0
instructions: list = []


def postprocess(data: dict):
    global part_counts, instructions, total_count, total_cost
    part_counts = defaultdict(lambda: {"count": 0, "name": "", "cost": 0})
    instructions = []
    total_count, total_cost = 0, 0
    data = data() if isinstance(data, Part) else data
    name = re.sub("v[0-9]+$", "", data["name"])
    data = {"connections": {"origin": data}, "name": "origin"}
    propagate_part_counts_in_part_json(data, 1)
    remove_unused_keys_from_part_json(data)
    data.pop("connections")
    data = {
        "name": name,
        "cost": total_cost,
        "count": total_count,
        "quantities": part_counts,
        "instructions": instructions,
    }
    return data


def propagate_part_counts_in_part_json(data: dict, multiplier: int):
    global part_counts, instructions, total_count, total_cost
    for k, v in data["connections"].items():
        v["count"] *= multiplier
        v["cost"] *= multiplier
        part_counts[v["forgeDocumentId"]]["count"] += v["count"]
        part_counts[v["forgeDocumentId"]]["cost"] += v["cost"]
        part_counts[v["forgeDocumentId"]]["name"] = re.sub("v[0-9]+$", "", v["name"])
        total_count += v["count"]
        total_cost += v["cost"]
        instructions.append(
            {
                "target": k,
                "source": v["provides"],
                "count": v["count"],
                "motion": v["motion"],
                "humanReadable": f"Connect {re.sub('v[0-9]+$', '', v['name'])} to {re.sub('v[0-9]+$', '', data['name'])}.",
            }
        )
        propagate_part_counts_in_part_json(v, v["count"])
    return data


def remove_unused_keys_from_part_json(data: dict):
    data.pop("requiredJointOriginsInfo", None)
    for k, v in data["connections"].items():
        remove_unused_keys_from_part_json(v)
    return data


def fast_json_to_string(content: dict):
    try:
        return orjson.dumps(content)
    except TypeError:
        try:
            return ujson.dumps(content, ensure_ascii=False).encode("utf-8")
        except OverflowError:
            return json.dumps(content, ensure_ascii=False).encode("utf-8")
