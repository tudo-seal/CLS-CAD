import json
from enum import Enum
from functools import partial, reduce

from picls import Arrow, Constructor, Subtypes, Type
from picls.dsl import DSL
from picls.types import Literal, Param, TVar

from cls_cps.cls_python.cls_json import CLSEncoder
from cls_cps.database.commands import get_all_parts_for_project
from cls_cps.util.motion import combine_motions


class Part:
    def __call__(self, *required_parts):
        return dict(
            self.info,
            count=1,
            connections={
                uuid: dict(
                    required_part()
                    if isinstance(required_part, Part)
                    else required_part,
                    count=uuid_info["count"],
                    motion=combine_motions(self.info["motion"], uuid_info["motion"]),
                )
                for (uuid, uuid_info), required_part in zip(
                    self.info["requiredJointOriginsInfo"].items(),
                    # We need to discard the information about the current counts
                    [part for part in required_parts if not isinstance(part, int)],
                )
            },
        )

    def __repr__(self):
        return self.__call__()

    def __str__(self):
        return ""

    def __hash__(self):
        return hash(json.dumps(self.info))

    def __init__(self, info):
        # Create combinator type here based on some JSON payload in future
        self.info = info

    def __eq__(self, other):
        return isinstance(other, Part) and self.__hash__() == other.__hash__()


class Role(str, Enum):
    requires = "requires"
    provides = "provides"


def add_literal_to_leaf(provides, part_counts, in_type, taxonomy):
    for count_type, count in part_counts:
        if taxonomy.check_subtype(provides, Constructor(count_type), dict()):
            in_type = in_type & Literal(1, count_type)
        else:
            in_type = in_type & Literal(0, count_type)
    return in_type


def collect_and_increment_part_count(count_type: str, counted_vars: dict):
    return sum([value for key, value in counted_vars.items() if count_type in key]) + 1


def collect_part_count(count_type: str, counted_vars: dict):
    return sum([value for key, value in counted_vars.items() if count_type in key])


def create_part_info(configuration, part_data):
    return dict(
        part_data["meta"],
        requiredJointOriginsInfo=fetch_required_joint_origins_info(
            part_data, configuration
        ),
        provides=configuration["providesJointOrigin"],
        motion=fetch_joint_origin_info(part_data, configuration["providesJointOrigin"])[
            "motion"
        ],
    )


def compute_new_count_for_count_type(config_types, count_type, part_type, taxonomy):
    if taxonomy.check_subtype(config_types[-1], Constructor(count_type), dict()):
        part_type = part_type.AsRaw(
            partial(collect_and_increment_part_count, count_type)
        )
    else:
        part_type = part_type.AsRaw(partial(collect_part_count, count_type))
    return part_type


def add_used_prefixes_to_part_type(
    count_type, ordered_list_of_configuration_uuids, part_type
):
    for uuid in ordered_list_of_configuration_uuids:
        part_type = part_type.Use(f"{uuid}_{count_type}", count_type)
    return part_type


def get_joint_origin_type(uuid: str, part: dict, role: Role, prefix=""):
    return Type.intersect(
        [Constructor(f"{prefix}{tpe}") for tpe in part["jointOrigins"][uuid][role]]
    )


def is_blacklisted_under_subtyping(
    blacklist, joint_origin_uuid, part, taxonomy, role: Role
):
    return bool(blacklist) and taxonomy.check_subtype(
        get_joint_origin_type(joint_origin_uuid, part, role),
        Type.intersect([Constructor(t) for t in blacklist]),
    )


def fetch_required_joint_origins_info(part, configuration):
    return {
        joint_origin_uuid: fetch_joint_origin_info(part, joint_origin_uuid)
        for joint_origin_uuid in configuration["requiresJointOrigins"]
    }


def fetch_joint_origin_info(part, joint_origin_uuid: str):
    return part["jointOrigins"][joint_origin_uuid]


def create_virtual_substitute_part(part, required_joint_origin_uuid):
    return Part(
        {
            "name": "clsconnectmarker_"
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
            "jointOrder": {},
            "provides": required_joint_origin_uuid,
            "motion": "Rigid",
        }
    )


def types_from_uuids(uuids: list, part: dict, prefix=""):
    return [
        *[get_joint_origin_type(x, part, Role.requires, prefix) for x in uuids[:-1]],
        *[get_joint_origin_type(uuids[-1], part, Role.provides, prefix)],
    ]


def multiarrow_from_types(type_list):
    return reduce(lambda a, b: Arrow(b, a), reversed(type_list))


def counting_multiarrow_from_uuid(uuid_list, count_type: str):
    return reduce(
        lambda a, b: Arrow(b, a),
        map(lambda uuid: TVar(f"{uuid}_{count_type}"), reversed(uuid_list)),
    )


def multiarrow_to_self(tpe, length):
    return multiarrow_from_types([tpe] * length)


class RepositoryBuilder:
    @staticmethod
    def add_part_to_repository(
        part_data: dict,
        repository: dict,
        *,
        part_counts: list[str, int] = None,
        blacklist=None,
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

        :param part_counts:
        :param part_data: The JSON representation of the part to add to the repository. This uses set() as its array type.
        :param repository: The repository dict for the part to be added to. This should be then used for synthesis.
        :param blacklist: An optional set that represent a Types.intersect([blacklist]).
        :param connect_uuid: The UUID of the joint the blacklist is based on.
        :param taxonomy: The taxonomy to check the blacklist with.
        :return:
        """
        for configuration in part_data["configurations"]:
            # Since SetDecoder is used for creating the part dict, we can just check if the part provides the leaf type
            # or an even more specific type, which we also can not allow.
            pass

            if is_blacklisted_under_subtyping(
                blacklist,
                configuration["providesJointOrigin"],
                part_data,
                taxonomy,
                Role.provides,
            ):
                continue

            ordered_list_of_configuration_uuids = [
                *configuration["requiresJointOrigins"],
                *[configuration["providesJointOrigin"]],
            ]

            config_types = types_from_uuids(
                ordered_list_of_configuration_uuids, part_data
            )
            in_type: Param = multiarrow_from_types(config_types)
            part_type = DSL()

            if len(config_types) == 1 and part_counts:
                in_type = add_literal_to_leaf(
                    config_types[-1], part_counts, in_type, taxonomy
                )

            if len(config_types) > 1 and part_counts:
                for count_type, count in part_counts:
                    part_type = add_used_prefixes_to_part_type(
                        count_type, ordered_list_of_configuration_uuids, part_type
                    )
                    part_type = compute_new_count_for_count_type(
                        config_types, count_type, part_type, taxonomy
                    )
                    in_type = in_type & counting_multiarrow_from_uuid(
                        ordered_list_of_configuration_uuids,
                        count_type,
                    )

            part_type = part_type.In(in_type)

            repository[
                Part(info=create_part_info(configuration, part_data))
            ] = part_type

            for required_joint_origin_uuid in configuration["requiresJointOrigins"]:
                # If a joint would require a blacklisted type or a subtype of it, we add that specific
                # version to the repository as a virtual Part along with a fitting PartConfig. This results in the
                # output JSON specifying that virtual part for the "back-side" of the synthesised connector.
                if not is_blacklisted_under_subtyping(
                    blacklist,
                    required_joint_origin_uuid,
                    part_data,
                    taxonomy,
                    Role.provides,
                ):
                    continue

                repository[
                    create_virtual_substitute_part(
                        part_data, required_joint_origin_uuid
                    )
                ] = get_joint_origin_type(
                    required_joint_origin_uuid, part_data, Role.requires
                )

    @staticmethod
    def add_all_to_repository(
        project_id: str,
        *,
        part_counts: list[[str, int]] = None,
        blacklist=None,
        connect_uuid=None,
        taxonomy=None,
    ):
        repository = {}
        for part_data in get_all_parts_for_project(project_id):
            RepositoryBuilder.add_part_to_repository(
                part_data,
                repository,
                part_counts=part_counts,
                blacklist=blacklist,
                connect_uuid=connect_uuid,
                taxonomy=taxonomy,
            )
        return repository
