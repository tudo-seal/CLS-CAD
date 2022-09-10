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

    def to_dict(self, motion="Rigid", count=1):
        return dict(
            name=self.info["partName"],
            provides=self.config.provides["uuid"],
            forgeDocumentId=self.info["forgeDocumentId"],
            forgeFolderId=self.info["forgeFolderId"],
            forgeProjectId=self.info["forgeProjectId"],
            count=count,
            motion=motion,
            connections={
                **{
                    jo_info["uuid"]: part.to_dict(
                        motion=combine_motions(
                            self.config.provides["motion"], jo_info["motion"]
                        ),
                        count=count * jo_info["count"],
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

    def __eq__(self, other):
        if self.__hash__() == other.__hash__():
            return True
        else:
            return False


# additional info about the parts configuration options
class PartConfig:
    def __init__(self, joint_order_info: list, provides):
        # Create combinator type here based on some JSON payload in future
        self.joint_order_info = joint_order_info
        self.provides = provides

    def __hash__(self):
        return hash(json.dumps(self.joint_order_info) + json.dumps(self.provides))

    def __eq__(self, other):
        if self.__hash__() == other.__hash__():
            return True
        else:
            return False


class RepositoryBuilder:
    @staticmethod
    def add_part_to_repository(
        part: dict,
        repository: dict,
        blacklist=set(),
        connect_uuid=None,
        taxonomy: Subtypes = None,
    ):
        """
        Adds a part to a repository to be used for synthesis. Adds necessary Constructors for the parts configurations,
        unless the configuration provides a blacklisted type. The blacklist is intended to be used for synthesising
        connectors, since a constructor for the type and its subtypes needs to be added but all productions for that
        type and its subtypes need to be removed. This guarantees that all results that request that type terminate in
        that Constructor or subtypes of it, which then indicate the point of connection.

        If a blacklist is provided, also adds Constructors for every encountered required type that is
        more specific than the blacklist.

        :param part: The JSON representation of the part to add to the repository. This uses set() as its array type.
        :param repository: The repository dict for the part to be added to. This should be then sued for synthesis.
        :param blacklist: An optional set that represent a Types.intersect([blacklist]).
        :param connect_uuid: The UUID of the joint the blacklist is based on.
        :param taxonomy: The taxonomy to check the blacklist with.
        :return:
        """
        for pc in part["partConfigs"]:
            # Since SetDecoder is used for creating the part dict, we can just check if the part provides the leaf type
            # or an even more specific type, which we also can not allow.
            if not (
                bool(blacklist)
                and taxonomy.check_subtype(
                    Type.intersect([Constructor(t) for t in pc["provides"]["types"]]),
                    Type.intersect([Constructor(t) for t in blacklist]),
                )
            ):
                repository[
                    PartConfig(pc["jointOrderInfo"], pc["provides"])
                ] = Constructor(
                    (
                        "_".join([x["uuid"] for x in pc["jointOrderInfo"]]) + "_"
                        if pc["jointOrderInfo"]
                        else ""
                    )
                    + pc["provides"]["uuid"]
                )
                for requirement in pc["jointOrderInfo"]:
                    # If a joint would require a blacklisted type or a subtype of it, we add that specific
                    # version to the repository as a virtual Part along with a fitting PartConfig. This results in the
                    # output JSON specifying that virtual part for the "back-side" of the synthesised connector.
                    if bool(blacklist) and taxonomy.check_subtype(
                        Type.intersect([Constructor(t) for t in requirement["types"]]),
                        Type.intersect([Constructor(t) for t in blacklist]),
                    ):
                        repository[
                            Part(
                                {
                                    "partName": f'clsconnectmarker_{"_".join(blacklist)}',
                                    "forgeDocumentId": "NoInsert",
                                    "forgeFolderId": "NoInsert",
                                    "forgeProjectId": "NoInsert",
                                }
                            )
                        ] = Arrow(
                            Constructor(connect_uuid),
                            Type.intersect(
                                [Constructor(t) for t in requirement["types"]]
                            ),
                        )
                        repository[
                            PartConfig(
                                [],
                                {"uuid": connect_uuid, "count": 1, "motion": "Rigid"},
                            )
                        ] = Constructor(connect_uuid)

        repository[Part(part["meta"])] = json.loads(
            json.dumps(part["combinator"]), cls=CLSDecoder
        )
        pass

    @staticmethod
    def add_all_to_repository(blacklist=set(), connect_uuid=None, taxonomy=None):
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
                    RepositoryBuilder.add_part_to_repository(
                        part, repository, blacklist, connect_uuid, taxonomy
                    )
        return repository
