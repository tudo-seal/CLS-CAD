import json
import os
from enum import Enum
from functools import reduce
from pathlib import Path

from bcls import Arrow, Constructor, Omega, Subtypes, Type
from bcls.debug_util import deep_str

from cls_cps.cls_python.cls_json import CLSEncoder
from cls_cps.util.motion import combine_motions
from cls_cps.util.set_json import SetDecoder


class Part:
    def __call__(self, config, *x):
        return dict(
            name=self.info["partName"],
            provides=config.provides["uuid"],
            forgeDocumentId=self.info["forgeDocumentId"],
            forgeFolderId=self.info["forgeFolderId"],
            forgeProjectId=self.info["forgeProjectId"],
            count=1,
            cost=self.info["cost"],
            availability=self.info["availability"],
            motion=config.provides["motion"],
            connections={
                **{
                    jo_info["uuid"]: dict(
                        part,
                        count=jo_info["count"],
                        motion=combine_motions(
                            config.provides["motion"], jo_info["motion"]
                        ),
                    )
                    for (jo_info, part) in zip(config.joint_order_info, x)
                }
            },
        )

    def __repr__(self):
        return ""

    def __str__(self):
        return ""

    @staticmethod
    def postprocess_part_json(data: dict):
        pass

    def __hash__(self):
        return hash(json.dumps(self.info))

    def __init__(self, info):
        # Create combinator type here based on some JSON payload in future
        self.info = info

    def __eq__(self, other):
        return isinstance(other, Part) and self.__hash__() == other.__hash__()


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
    return Type.intersect(
        [Constructor(tpe) for tpe in part["jointOrigins"][uuid][role]]
    )


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
    return reduce(lambda a, b: Arrow(b, a), reversed(type_list))


def multiarrow_to_self(tpe, length):
    return multiarrow_from_types([tpe] * length)


def intersect_all_multiarrows_containing_type(tpe, length):
    result = []
    for x in range(1, length - 1):
        multiarrow_type_list = [Omega()] * length
        multiarrow_type_list[x] = tpe
        multiarrow_type_list[-1] = tpe
        print(deep_str(multiarrow_type_list))
        print(multiarrow_from_types(multiarrow_type_list))
        result.append(multiarrow_from_types(multiarrow_type_list))
    return Type.intersect(result)


class RepositoryBuilder:
    @staticmethod
    def add_part_to_repository(
        part: dict,
        repository: dict,
        *,
        blacklist=set(),
        connect_uuid=None,
        taxonomy: Subtypes = None,
        passed_through_types=[]
    ):
        """
        Adds a part to a repository to be used for synthesis. Adds necessary Constructors for the parts configurations,
        unless the configuration provides a blacklisted type. The blacklist is intended to be used for synthesising
        connectors, since a constructor for the type and its subtypes needs to be added but all productions for that
        type and its subtypes need to be removed. This guarantees that all results that request that type terminate in
        that Constructor or subtypes of it, which then indicate the point of connection.

        If a blacklist is provided, also adds Constructors for every encountered required type that is
        more specific than the blacklist.

        :param passed_through_types:
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

            config_types = types_from_uuids(ordered_list_of_configuration_uuids, part)
            config_multiarrow = Arrow(
                Constructor("-".join(ordered_list_of_configuration_uuids)),
                multiarrow_from_types(config_types),
            )

            if passed_through_types:
                passed_through_types_intersections = [
                    intersect_all_multiarrows_containing_type(
                        Constructor(tpe), len(config_types) + 1
                    )
                    for tpe in passed_through_types
                ]

                config_multiarrow = Type.intersect(
                    [*[config_multiarrow], *passed_through_types_intersections]
                )
            configuration_types.append(config_multiarrow)

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
        passed_through_types=[]
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
                        passed_through_types=passed_through_types,
                    )
        return repository
