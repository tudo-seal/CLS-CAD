import copy
import json
import re
from collections import defaultdict, deque

base_json = True
try:
    import orjson
    import ujson

    base_json = False
except ImportError:
    pass

from cls_cps.repository_builder import Part
from cls_cps.util.hrid import generate_id


def postprocess(data: dict):
    data = data() if isinstance(data, Part) else data
    name = re.sub("v[0-9]+$", "", data["name"])
    data = {"connections": {"origin": data}, "name": "origin", "count": 1}
    data = resolve_multiplicity(data)
    part_counts, total_count, total_cost = compute_insertions_and_totals(data)
    instructions, link_index = compute_instructions(data)
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


def resolve_multiplicity(data: dict):
    connection_list = []
    for k, v in data["connections"].items():
        v["count"] *= data["count"]
        if v["motion"] != "Rigid":
            for i in range(v["count"]):
                separate_link_beginning = copy.deepcopy(v)
                separate_link_beginning["count"] = 1
                connection_list.append((k, separate_link_beginning))
            continue
        v["cost"] *= v["count"]
        connection_list.append((k, v))
    data["connections"] = connection_list
    for k, v in data["connections"]:
        resolve_multiplicity(v)
    return data


def compute_insertions_and_totals(data: dict):
    part_counts = defaultdict(lambda: {"count": 0, "name": "", "cost": 0})
    total_count, total_cost = 0, 0
    to_traverse = deque(data["connections"])
    while to_traverse:
        k, v = to_traverse.popleft()
        part_counts[v["forgeDocumentId"]]["count"] += v["count"]
        part_counts[v["forgeDocumentId"]]["cost"] += v["cost"]
        part_counts[v["forgeDocumentId"]]["name"] = re.sub("v[0-9]+$", "", v["name"])
        total_count += v["count"]
        total_cost += v["cost"]
        to_traverse.extend(v["connections"])
    return part_counts, total_count, total_cost


def compute_instructions(data):
    instructions = []
    idx = 0
    to_traverse = deque([list(tup) + [idx] for tup in data["connections"]])
    while to_traverse:
        k, v, idx = to_traverse.popleft()
        if v["motion"] != "Rigid":
            idx += 1
        to_traverse.extend([list(tup) + [idx] for tup in v["connections"]])
        instructions.append(
            {
                "target": k,
                "source": v["provides"],
                "move": v["forgeDocumentId"],
                "count": 1 if v["motion"] != "Rigid" else v["count"],
                "motion": v["motion"],
                "link": f"link{idx}",
            }
        )
    return instructions, idx


def remove_unused_keys_from_part_json(data: dict):
    data.pop("requiredJointOriginsInfo", None)
    for k, v in data["connections"]:
        remove_unused_keys_from_part_json(v)
    return data


def invert_taxonomy(taxonomy):
    if not taxonomy:
        return {
            "taxonomies": {
                "parts": {"Part": []},
                "formats": {"Format": []},
                "attributes": {"Attribute": []},
            },
            "mappings": {
                "parts": {"Part": generate_id()},
                "formats": {"Format": generate_id()},
                "attributes": {"Attribute": generate_id()},
            },
        }

    inverted_taxonomy = {"taxonomies": {}, "mappings": taxonomy["mappings"]}
    for key, individual_taxonomy in taxonomy["taxonomies"].items():
        inverted_taxonomy["taxonomies"][key] = invert_sub_taxonomy(individual_taxonomy)
        inverted_taxonomy["taxonomies"][key] = {
            key.capitalize()[:-1]: inverted_taxonomy["taxonomies"][key].pop(
                key.capitalize()[:-1], []
            ),
            **inverted_taxonomy["taxonomies"][key],
        }
    return inverted_taxonomy


def invert_sub_taxonomy(sub_taxonomy):
    subtypes = defaultdict(list)
    for key, values in sub_taxonomy.items():
        subtypes[key] = subtypes[key]
        for value in values:
            subtypes[value].append(key)
    return subtypes


def suffix_taxonomy_and_add_mirror(taxonomy: dict):
    suffixed_taxonomy = {}
    for key, individual_taxonomy in taxonomy["taxonomies"].items():
        suffixed_individual_taxonomy = {}
        for entry in individual_taxonomy:
            suffixed_individual_taxonomy[f"{entry}_{key}"] = [
                f"{name}_{key}" for name in individual_taxonomy[entry]
            ]
            suffixed_individual_taxonomy[f"Has_{entry}_{key}"] = [
                f"Has_{name}_{key}" for name in individual_taxonomy[entry]
            ]
        suffixed_taxonomy.update(suffixed_individual_taxonomy)
    return suffixed_taxonomy


def fast_json_to_string(content: dict):
    if base_json:
        return json.dumps(content, ensure_ascii=False).encode("utf-8")
    try:
        return orjson.dumps(content)
    except TypeError:
        try:
            return ujson.dumps(content, ensure_ascii=False).encode("utf-8")
        except OverflowError:
            return json.dumps(content, ensure_ascii=False).encode("utf-8")
