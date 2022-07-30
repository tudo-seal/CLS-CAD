import json
import os
from pathlib import Path

from cls_python import *
from util.motion import combine_motions
from util.set_json import SetDecoder


class Jsonify:
    def __call__(self, x):
        return Jsonify(self.config, [*self.data, x], self.info)

    def __str__(self):
        return deep_str(self.data)

    def __init__(self, config, data, info):
        self.config = config
        self.data = data
        self.info = info

    def to_dict(self, motion="Rigid"):
        return dict(
            name=self.info["partName"],
            provides=self.config.provides["uuid"],
            forgeDocumentId=self.info["forgeDocumentId"],
            forgeFolderId=self.info["forgeFolderId"],
            forgeProjectId=self.info["forgeProjectId"],
            motion=motion,
            connections={
                **{
                    jo_info["uuid"]: part.to_dict(
                        motion=combine_motions(
                            self.config.provides["motion"], jo_info["motion"]
                        )
                    )
                    for (jo_info, part) in zip(self.config.joint_order_info, self.data)
                }
            },
        )


class Part(object):
    def __call__(self, x):
        return Jsonify(x, [], self.info)

    def __repr__(self):
        return ""

    def __str__(self):
        return ""

    def __eq__(self, other):
        return isinstance(other, Part)

    def __hash__(self):
        return hash(json.dumps(self.info))

    def __init__(self, info):
        # Create combinator type here based on some JSON payload in future
        self.info = info


# additional info about the parts configuration options
class PartConfig:
    def __init__(self, joint_order_info: list, provides):
        # Create combinator type here based on some JSON payload in future
        self.joint_order_info = joint_order_info
        self.provides = provides


class RepositoryBuilder:
    @staticmethod
    def add_part_to_repository(part: dict, repository: dict):
        for pc in part["partConfigs"]:
            repository[PartConfig(pc["jointOrderInfo"], pc["provides"])] = Constructor(
                (
                    "_".join([x["uuid"] for x in pc["jointOrderInfo"]]) + "_"
                    if pc["jointOrderInfo"]
                    else ""
                )
                + pc["provides"]["uuid"]
            )
        repository[Part(part["meta"])] = json.loads(
            json.dumps(part["combinator"]), cls=CLSDecoder
        )
        pass

    @staticmethod
    def add_all_to_repository():
        repository = {}
        with open("Repositories/CAD/index.dat", "r+") as f:
            data = json.load(f, cls=SetDecoder)
            part = None
            for key, value in data["parts"].items():
                p = Path(
                    os.path.join(
                        "Repositories",
                        "CAD",
                        value["forgeProjectId"],
                        value["forgeFolderId"],
                    ).replace(":", "-")
                )
                with (p / key.replace(":", "-")).open("r") as fp:
                    part = json.load(fp)
                    RepositoryBuilder.add_part_to_repository(part, repository)
        return repository
