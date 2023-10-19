# import json
# import os
# import sys
# from pathlib import Path
#
# from picls import FiniteCombinatoryLogic, Subtypes
#
# from cls_cad_backend.cls_python.cls_json import CLSDecoder
# from cls_cad_backend.repository_builder import RepositoryBuilder
# from cls_cad_backend.util.set_json import SetDecoder
#
# hypermapper_project_id = ""
#
#
# def create_hypermapper_config(uuid: str, project_id: str, targets: list):
#     """
#     Generates config for running hypermapper on a CLS-CAD repository.
#
#     :param uuid: Used for naming output and output folder.
#     :param project_id: Only parts found in this project are added to the parameters.
#     :param targets: A list of cls-json encoded strings with synthesis targets.
#     :return:
#     """
#     config_dict = {
#         "input_parameters": dict(),
#         "application_name": project_id + "_" + uuid,
#         "optimization_objectives": ["Cost", "Count", "Availability"],
#         "optimization_iterations": 5,
#         "number_of_cpus": 1,
#         "run_directory": f"Results/Hypermapper/{project_id}/{uuid}",
#         "output_data_file": "samples.csv",
#         "output_pareto_file": "pareto.csv",
#         "number_of_repetitions": 1,
#         "feasible_output": {
#             "name": "Valid",
#             "true_value": True,
#             "false_value": False,
#             "enable_feasible_predictor": True,
#         },
#         "print_parameter_importance": True,
#         "optimization_method": "bayesian_optimization",
#     }
#     with open("Repositories/CAD/index.dat", "r+") as f:
#         data = json.load(f, cls=SetDecoder)
#         # Scale DoE Phase with size of repository
#         config_dict["design_of_experiment"] = {
#             "doe_type": "random sampling",
#             "number_of_samples": len(data["projects"][project_id]["documents"]),
#         }
#         for entry in data["projects"][project_id]["documents"]:
#             config_dict["input_parameters"][entry.rsplit(":", 1)[-1]] = {
#                 "parameter_type": "ordinal",
#                 "values": [0, 1],
#                 "parameter_default": 1,
#             }
#         config_dict["input_parameters"]["target"] = {
#             "parameter_type": "categorical",
#             "values": targets,
#         }
#     global hypermapper_project_id
#     hypermapper_project_id = project_id
#     return config_dict
#
#
# def wrapped_synthesis_optimization_function(X):
#     repository = {}
#     with open("Repositories/CAD/index.dat", "r+") as f:
#         data = json.load(f, cls=SetDecoder)
#         for key, value in X.items():
#             if key == "target":
#                 continue
#             if value:
#                 p = Path(
#                     os.path.join(
#                         "Repositories",
#                         "CAD",
#                         data["parts"][f"urn:adsk.wipprod:dm.lineage:{key}"][
#                             "forgeProjectId"
#                         ],
#                         data["parts"][f"urn:adsk.wipprod:dm.lineage:{key}"][
#                             "forgeFolderId"
#                         ],
#                     ).replace(":", "-")
#                 )
#                 with (p / f"urn-adsk.wipprod-dm.lineage-{key}").open("r") as fp:
#                     part = json.load(fp)
#                     RepositoryBuilder.add_part_to_repository(part, repository)
#     taxonomy = Subtypes(
#         json.load(
#             open(f"Taxonomies/CAD/{hypermapper_project_id}/taxonomy.dat"),
#             cls=SetDecoder,
#         )
#     )
#     gamma = FiniteCombinatoryLogic(
#         repository,
#         taxonomy,
#         processes=1,
#     )
#     result = gamma.inhabit(json.loads(X["target"], cls=CLSDecoder))
#
#     optimization_metrics = {"Count": 0, "Cost": 0, "Availability": 0, "Valid": True}
#     if result.size() == 0:
#         return {
#             "Count": sys.float_info.max,
#             "Cost": sys.float_info.max,
#             "Availability": sys.float_info.max,
#             "Valid": False,
#         }
#     if result.size() > 0:
#         for i in range(result.size()):
#             single_result_metrics = json_to_multiobjective_value(
#                 result.evaluated[i].to_dict()
#             )
#             optimization_metrics["Count"] += single_result_metrics["Count"]
#             optimization_metrics["Cost"] += single_result_metrics["Cost"]
#             optimization_metrics["Availability"] += single_result_metrics[
#                 "Availability"
#             ]
#     else:
#         # Grab the smallest 100 and aggregate them
#         for i in range(100):
#             single_result_metrics = json_to_multiobjective_value(
#                 result.evaluated[i].to_dict()
#             )
#             optimization_metrics["Count"] += single_result_metrics["Count"]
#             optimization_metrics["Cost"] += single_result_metrics["Cost"]
#             optimization_metrics["Availability"] += single_result_metrics[
#                 "Availability"
#             ]
#     return optimization_metrics
#
#
# def json_to_multiobjective_value(assembly_layer: dict):
#     optimization_metrics = {
#         "Count": assembly_layer["count"],
#         "Cost": assembly_layer["cost"],
#         "Availability": 1.0 - assembly_layer["availability"],
#     }
#     # Aggregate are our own values plus the values of all our connections
#     # The JSON already has corrected counts and costs for branching, which makes it very simple here
#     for key, connection in assembly_layer["connections"].items():
#         next_assembly_layer_metrics = json_to_multiobjective_value(connection)
#         optimization_metrics["Count"] += next_assembly_layer_metrics["Count"]
#         optimization_metrics["Cost"] += next_assembly_layer_metrics["Cost"]
#         optimization_metrics["Availability"] += next_assembly_layer_metrics[
#             "Availability"
#         ]
#     return optimization_metrics
