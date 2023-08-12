# import json
#
# import numpy as np
# import pandas as pd
# import plotly.express as px
#
# # Taken from https://stackoverflow.com/questions/32791911/fast-calculation-of-pareto-front-in-python
# from cls_cps.util.set_json import SetDecoder
#
#
# def is_pareto_efficient(costs, return_mask=True):
#     """
#     Find the pareto-efficient points
#     :param costs: An (n_points, n_costs) array
#     :param return_mask: True to return a mask
#     :return: An array of indices of pareto-efficient points.
#         If return_mask is True, this will be an (n_points, ) boolean array
#         Otherwise it will be a (n_efficient_points, ) integer array of indices.
#     """
#     is_efficient = np.arange(costs.shape[0])
#     n_points = costs.shape[0]
#     next_point_index = 0  # Next index in the is_efficient array to search for
#     while next_point_index < len(costs):
#         nondominated_point_mask = np.any(costs < costs[next_point_index], axis=1)
#         nondominated_point_mask[next_point_index] = True
#         is_efficient = is_efficient[nondominated_point_mask]  # Remove dominated points
#         costs = costs[nondominated_point_mask]
#         next_point_index = np.sum(nondominated_point_mask[:next_point_index]) + 1
#     if return_mask:
#         is_efficient_mask = np.zeros(n_points, dtype=bool)
#         is_efficient_mask[is_efficient] = True
#         return is_efficient_mask
#     else:
#         return is_efficient
#
#
# def compute_pareto_front(path: str):
#     df = pd.read_csv(f"{path}/samples.csv")
#     df.drop(df[df["Valid"] == False].index, inplace=True)
#     df["Configuration Vector"] = df.iloc[:, :-6].values.tolist()
#     configuration_info = list(df.columns.values)[:-7]
#     df.drop(
#         df.columns.difference(
#             ["Cost", "Count", "Availability", "Configuration Vector"]
#         ),
#         1,
#         inplace=True,
#     )
#     # Apply pareto boolean mask
#     df["Mask"] = is_pareto_efficient(df.to_numpy())
#     df.drop(df[df["Mask"] == False].index, inplace=True)
#     df.drop("Mask", axis=1, inplace=True)
#
#     df.to_csv(f"{path}/pareto.csv", sep=",", encoding="utf-8")
#     with open("Repositories/CAD/index.dat", "r+") as idx:
#         data = json.load(idx, cls=SetDecoder)
#         with open(
#             f"{path}/config_vector_info.json",
#             "w+",
#         ) as f:
#             f.write(",".join(configuration_info) + "\n")
#             f.write(
#                 ",".join(
#                     [
#                         data["parts"][f"urn:adsk.wipprod:dm.lineage:{x}"]["name"]
#                         for x in configuration_info
#                     ]
#                 )
#             )
#     return df
#
#
# def visualize_pareto_front(df, path: str):
#     fig = px.scatter_3d(df, x="Cost", y="Count", z="Availability")
#     fig.write_html(f"{path}/pareto.html")
