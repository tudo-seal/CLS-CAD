import json
import re
from collections import defaultdict, deque

import ujson
from orjson import orjson

from cls_cps.repository_builder import Part

part_counts: defaultdict = defaultdict(lambda: {"count": 0, "name": "", "cost": 0})
total_count, total_cost = 0, 0
instructions: list = []
links: defaultdict = defaultdict(lambda: defaultdict(int))


def postprocess(data: dict):
    global part_counts, instructions, total_count, total_cost, links
    part_counts = defaultdict(lambda: {"count": 0, "name": "", "cost": 0})
    links = defaultdict(lambda: defaultdict(int))
    instructions = []
    total_count, total_cost = 0, 0
    data = data() if isinstance(data, Part) else data
    name = re.sub("v[0-9]+$", "", data["name"])
    data = {"connections": {"origin": data}, "name": "origin", "count": 1}
    data = propagate_part_counts_in_part_json(data)
    link_index = compute_instructions(data)
    remove_unused_keys_from_part_json(data)
    data.pop("connections")
    data = {
        "name": name,
        "cost": total_cost,
        "count": total_count,
        "quantities": part_counts,
        "links": link_index + 1,
        "instructions": instructions,
    }
    return data


def propagate_part_counts_in_part_json(data: dict):
    global part_counts, total_count, total_cost
    for v in data["connections"].values():
        v["count"] *= data["count"]
        v["cost"] *= v["count"]
        part_counts[v["forgeDocumentId"]]["count"] += v["count"]
        part_counts[v["forgeDocumentId"]]["cost"] += v["cost"]
        part_counts[v["forgeDocumentId"]]["name"] = re.sub("v[0-9]+$", "", v["name"])
        total_count += v["count"]
        total_cost += v["cost"]
        propagate_part_counts_in_part_json(v)
    return data


def compute_instructions(data):
    global instructions
    idx = 0
    to_traverse = deque([list(tup) + [idx] for tup in data["connections"].items()])
    while to_traverse:
        k, v, idx = to_traverse.popleft()
        if v["motion"] != "Rigid":
            idx += 1
        to_traverse.extend([list(tup) + [idx] for tup in v["connections"].items()])
        instructions.append(
            {
                "target": k,
                "source": v["provides"],
                "move": v["forgeDocumentId"],
                "count": v["count"],
                "motion": v["motion"],
                "link": f"link{idx}",
            }
        )
    return idx


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
