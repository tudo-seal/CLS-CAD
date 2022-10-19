import json
import os
from pathlib import Path

from cls_python import (
    Arrow,
    CLSDecoder,
    CLSEncoder,
    Constructor,
    Subtypes,
    Type,
    deep_str,
)
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
            cost=count * self.info["cost"],
            availability=self.info["availability"],
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


class Part:
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


def get_joint_origin_required_type(uuid: str, part):
    return json.loads(
        json.dumps(part["jointOrigins"][uuid]["requires"]), cls=CLSDecoder
    )


def get_joint_origin_provided_type(uuid: str, part):
    return json.loads(
        json.dumps(part["jointOrigins"][uuid]["provides"]), cls=CLSDecoder
    )


class RepositoryBuilder:
    @staticmethod
    def arrow_concat_list(type_list, part: dict):
        if len(type_list) == 1:
            return get_joint_origin_provided_type(type_list[0], part)
        return Arrow(
            get_joint_origin_required_type(type_list.pop(0), part),
            RepositoryBuilder.arrow_concat_list(type_list, part),
        )

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
        for configuration in part["configurations"]:
            # Since SetDecoder is used for creating the part dict, we can just check if the part provides the leaf type
            # or an even more specific type, which we also can not allow.
            configuration_types = []
            # If not blacklisted, add the partial combinator that will be part of the large intersection to the list
            # And then add the PartConfig for that Config to the Repository immediately
            if not (
                bool(blacklist)
                and taxonomy.check_subtype(
                    get_joint_origin_provided_type(
                        configuration["providesJointOrigin"], part
                    ),
                    Type.intersect([Constructor(t) for t in blacklist]),
                )
            ):
                configuration_types.append(
                    Arrow(
                        Constructor(
                            "-".join(
                                configuration["requiresJointOrigins"]
                                + [configuration["providesJointOrigin"]]
                            )
                        ),
                        RepositoryBuilder.arrow_concat_list(
                            configuration["requiresJointOrigins"]
                            + [configuration["providesJointOrigin"]],
                            part,
                        ),
                    )
                )
                repository[
                    PartConfig(
                        [
                            dict(part["jointOrigins"][x], **{"uuid": x})
                            for x in configuration["requiresJointOrigins"]
                        ],
                        dict(
                            part["jointOrigins"][configuration["providesJointOrigin"]],
                            **{"uuid": configuration["providesJointOrigin"]},
                        ),
                    )
                ] = Constructor(
                    "-".join(
                        configuration["requiresJointOrigins"]
                        + [configuration["providesJointOrigin"]]
                    )
                )

                for required_joint_origin_uuid in configuration["requiresJointOrigins"]:
                    # If a joint would require a blacklisted type or a subtype of it, we add that specific
                    # version to the repository as a virtual Part along with a fitting PartConfig. This results in the
                    # output JSON specifying that virtual part for the "back-side" of the synthesised connector.
                    if bool(blacklist) and taxonomy.check_subtype(
                        get_joint_origin_required_type(
                            required_joint_origin_uuid, part
                        ),
                        Type.intersect([Constructor(t) for t in blacklist]),
                    ):
                        repository[
                            Part(
                                {
                                    "partName": "clsconnectmarker_"
                                    + str(
                                        hash(
                                            json.dumps(
                                                get_joint_origin_required_type(
                                                    required_joint_origin_uuid, part
                                                ),
                                                cls=CLSEncoder,
                                            )
                                        )
                                    ),
                                    "forgeDocumentId": "NoInsert",
                                    "forgeFolderId": "NoInsert",
                                    "forgeProjectId": "NoInsert",
                                }
                            )
                        ] = Arrow(
                            Constructor(connect_uuid),
                            get_joint_origin_required_type(
                                required_joint_origin_uuid, part
                            ),
                        )
                        repository[
                            PartConfig(
                                [],
                                {"uuid": connect_uuid, "count": 1, "motion": "Rigid"},
                            )
                        ] = Constructor(connect_uuid)

        repository[Part(part["meta"])] = Type.intersect(configuration_types)

    @staticmethod
    def add_all_to_repository(
        project_id: str, blacklist=set(), connect_uuid=None, taxonomy=None
    ):
        repository = {}
        with open("Repositories/CAD/index.dat", "r+") as f:
            data = json.load(f, cls=SetDecoder)
            for entry in data["projects"][project_id]["documents"]:
                p = Path(
                    os.path.join(
                        "Repositories",
                        "CAD",
                        data["parts"][entry]["forgeProjectId"],
                        data["parts"][entry]["forgeFolderId"],
                    ).replace(":", "-")
                )
                with (p / entry.replace(":", "-")).open("r") as fp:
                    part = json.load(fp)
                    RepositoryBuilder.add_part_to_repository(
                        part, repository, blacklist, connect_uuid, taxonomy
                    )
        return repository
