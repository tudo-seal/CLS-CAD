import json
import os
import sys
from pathlib import Path

from cls_python import Subtypes, FiniteCombinatoryLogic, CLSDecoder
from repository_builder import RepositoryBuilder
from util.set_json import SetDecoder


hypermapper_project_id = ""


def write_hypermapper_config(project_id: str, targets: list):
    """
    Generates config for running hypermapper on a CLS-CAD repository.

    :param project_id: Only parts found in this project are added to the parameters.
    :param targets: A list of cls-json encoded strings with synthesis targets.
    :return:
    """
    config_dict = {
        "input_parameters": dict,
        "application_name": project_id + "_" + str(hash(targets)),
        "optimization_objectives": ["Cost", "Count", "Availability"],
        "optimization_iterations": 50,
    }
    with open("Repositories/CAD/index.dat", "r+") as f:
        data = json.load(f, cls=SetDecoder)
        for entry in data["projects"][project_id]["documents"]:
            config_dict["input_parameters"][entry] = {
                "parameter_type": "ordinal",
                "values": [0, 1],
            }
        config_dict["input_parameters"]["target"] = {
            "parameter_type": "categorical",
            "values": targets,
        }
    global hypermapper_project_id
    hypermapper_project_id = project_id
    pass


def wrapped_synthesis_optimisation_function(X):
    repository = {}
    with open("Repositories/CAD/index.dat", "r+") as f:
        data = json.load(f, cls=SetDecoder)
        for key, value in X.items():
            if key == "target":
                continue
            if value:
                p = Path(
                    os.path.join(
                        "Repositories",
                        "CAD",
                        data["parts"][key]["forgeProjectId"],
                        data["parts"][key]["forgeFolderId"],
                    ).replace(":", "-")
                )
                with (p / key.replace(":", "-")).open("r") as fp:
                    part = json.load(fp)
                    RepositoryBuilder.add_part_to_repository(part, repository)
    taxonomy = Subtypes(
        json.load(
            open(f"Taxonomies/CAD/{hypermapper_project_id}/taxonomy.dat", "r"),
            cls=SetDecoder,
        )
    )
    gamma = FiniteCombinatoryLogic(
        repository,
        taxonomy,
        processes=1,
    )
    result = gamma.inhabit(json.loads(X["target"], cls=CLSDecoder))

    optimization_metrics = {
        "Count": 0,
        "Cost": 0,
        "Availability": 0,
    }
    if result.size() == 0:
        return {
            "Count": sys.float_info.max,
            "Cost": sys.float_info.max,
            "Availability": sys.float_info.max,
        }
    if result.size() > 0:
        for i in range(result.size()):
            single_result_metrics = json_to_multiobjective_value(
                result.evaluated[i].to_dict()
            )
            optimization_metrics["Count"] += single_result_metrics["Count"]
            optimization_metrics["Cost"] += single_result_metrics["Cost"]
            optimization_metrics["Availability"] += single_result_metrics[
                "Availability"
            ]
    else:
        # Grab the smallest 100 and aggregate them
        for i in range(100):
            single_result_metrics = json_to_multiobjective_value(
                result.evaluated[i].to_dict()
            )
            optimization_metrics["Count"] += single_result_metrics["Count"]
            optimization_metrics["Cost"] += single_result_metrics["Cost"]
            optimization_metrics["Availability"] += single_result_metrics[
                "Availability"
            ]
    return optimization_metrics


def json_to_multiobjective_value(assembly_layer: dict):
    optimization_metrics = {
        "Count": assembly_layer["count"],
        "Cost": assembly_layer["cost"],
        "Availability": 1.0 - assembly_layer["availability"],
    }
    # Aggregate are our own values plus the values of all our connections
    # The JSON already has corrected counts and costs for branching, which makes it very simple here
    for key, connection in assembly_layer["connections"].items():
        next_assembly_layer_metrics = json_to_multiobjective_value(connection)
        optimization_metrics["Count"] += next_assembly_layer_metrics["Count"]
        optimization_metrics["Cost"] += next_assembly_layer_metrics["Cost"]
        optimization_metrics["Availability"] += next_assembly_layer_metrics[
            "Availability"
        ]
    return optimization_metrics
