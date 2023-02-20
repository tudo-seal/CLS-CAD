import json
import os
from enum import Enum
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


class Role(str, Enum):
    requires = "requires"
    provides = "provides"


def get_joint_origin_type(uuid: str, part: dict, role: Role):
    return json.loads(json.dumps(part["jointOrigins"][uuid][role]), cls=CLSDecoder)


def is_blacklisted_under_subtyping(
    blacklist, joint_origin_uuid, part, taxonomy, role: Role
):
    return bool(blacklist) and taxonomy.check_subtype(
        get_joint_origin_type(joint_origin_uuid, part, role),
        Type.intersect([Constructor(t) for t in blacklist]),
    )


def create_part_config_combinator(part, configuration):
    return PartConfig(
        [
            dict(part["jointOrigins"][x], **{"uuid": x})
            for x in configuration["requiresJointOrigins"]
        ],
        dict(
            part["jointOrigins"][configuration["providesJointOrigin"]],
            **{"uuid": configuration["providesJointOrigin"]},
        ),
    )


def create_virtual_substitute_part(part, required_joint_origin_uuid):
    return Part(
        {
            "partName": "clsconnectmarker_"
            + str(
                hash(
                    json.dumps(
                        get_joint_origin_type(
                            required_joint_origin_uuid, part, Role.requires
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


def types_from_uuids(uuids: list, part: dict):
    return [
        *[get_joint_origin_type(x, part, Role.requires) for x in uuids[:-1]],
        *[get_joint_origin_type(uuids[-1], part, Role.provides)],
    ]


def multiarrow_from_types(type_list):
    arrow = type_list.pop()
    for x in reversed(type_list):
        arrow = Arrow(x, arrow)
    return arrow


class RepositoryBuilder:
    @staticmethod
    def add_part_to_repository(
        part: dict,
        repository: dict,
        *,
        blacklist=set(),
        connect_uuid=None,
        taxonomy: Subtypes = None,
        passed_through_types=None
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
        :param repository: The repository dict for the part to be added to. This should be then used for synthesis.
        :param blacklist: An optional set that represent a Types.intersect([blacklist]).
        :param connect_uuid: The UUID of the joint the blacklist is based on.
        :param taxonomy: The taxonomy to check the blacklist with.
        :return:
        """
        for configuration in part["configurations"]:
            # Since SetDecoder is used for creating the part dict, we can just check if the part provides the leaf type
            # or an even more specific type, which we also can not allow.
            configuration_types = []

            if is_blacklisted_under_subtyping(
                blacklist,
                configuration["providesJointOrigin"],
                part,
                taxonomy,
                Role.provides,
            ):
                continue

            ordered_list_of_configuration_uuids = [
                *configuration["requiresJointOrigins"],
                *[configuration["providesJointOrigin"]],
            ]

            configuration_types.append(
                Arrow(
                    Constructor("-".join(ordered_list_of_configuration_uuids)),
                    multiarrow_from_types(
                        types_from_uuids(ordered_list_of_configuration_uuids, part)
                    ),
                )
            )
            repository[
                create_part_config_combinator(part, configuration)
            ] = Constructor("-".join(ordered_list_of_configuration_uuids))

            for required_joint_origin_uuid in configuration["requiresJointOrigins"]:
                # If a joint would require a blacklisted type or a subtype of it, we add that specific
                # version to the repository as a virtual Part along with a fitting PartConfig. This results in the
                # output JSON specifying that virtual part for the "back-side" of the synthesised connector.
                if not is_blacklisted_under_subtyping(
                    blacklist, required_joint_origin_uuid, part, taxonomy, Role.provides
                ):
                    continue

                repository[
                    create_virtual_substitute_part(part, required_joint_origin_uuid)
                ] = Arrow(
                    Constructor(connect_uuid),
                    get_joint_origin_type(
                        required_joint_origin_uuid, part, Role.requires
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
        project_id: str,
        *,
        blacklist=set(),
        connect_uuid=None,
        taxonomy=None,
        passed_through_types=None
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
                        part,
                        repository,
                        blacklist=blacklist,
                        connect_uuid=connect_uuid,
                        taxonomy=taxonomy,
                    )
        return repository
