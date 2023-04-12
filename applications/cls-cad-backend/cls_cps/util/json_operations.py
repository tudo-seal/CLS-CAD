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
    data = {"connections": {"origin": data}, "name": "origin", "count": 1}
    propagate_part_counts_in_part_json(data)
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


def propagate_part_counts_in_part_json(data: dict):
    global part_counts, instructions, total_count, total_cost
    for k, v in data["connections"].items():
        v["count"] *= data["count"]
        v["cost"] *= v["count"]
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
        propagate_part_counts_in_part_json(v)
    return data


def remove_unused_keys_from_part_json(data: dict):
    data.pop("requiredJointOriginsInfo", None)
    for k, v in data["connections"].items():
        remove_unused_keys_from_part_json(v)
    return data


def invert_taxonomy(taxonomy):
    inverted_taxonomy = {}
    if not taxonomy:
        return {
            "parts": {"Part": []},
            "formats": {"Format": []},
            "attributes:": {"Attribute": []},
        }
    for key, individual_taxonomy in taxonomy["taxonomies"].items():
        inverted_taxonomy[key] = invert_sub_taxonomy(individual_taxonomy)
        inverted_taxonomy[key] = {
            key.capitalize()[:-1]: inverted_taxonomy[key].pop(key.capitalize()[:-1]),
            **inverted_taxonomy[key],
        }
    return inverted_taxonomy


def invert_sub_taxonomy(sub_taxonomy):
    subtypes = defaultdict(list)
    for key, values in sub_taxonomy.items():
        subtypes[key] = subtypes[key]
        for value in values:
            subtypes[value].append(key)
    return subtypes


def suffix_taxonomy(taxonomy):
    suffixed_taxonomy = {}
    for key, individual_taxonomy in taxonomy["taxonomies"].items():
        suffixed_individual_taxonomy = {}
        for entry in individual_taxonomy:
            suffixed_individual_taxonomy[f"{entry}_{key}"] = [
                f"{name}_{key}" for name in individual_taxonomy[entry]
            ]
        suffixed_taxonomy.update(suffixed_individual_taxonomy)
    return suffixed_taxonomy


def fast_json_to_string(content: dict):
    try:
        return orjson.dumps(content)
    except TypeError:
        try:
            return ujson.dumps(content, ensure_ascii=False).encode("utf-8")
        except OverflowError:
            return json.dumps(content, ensure_ascii=False).encode("utf-8")
