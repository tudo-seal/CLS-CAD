import json
from collections import OrderedDict, defaultdict
from collections.abc import Mapping
from enum import Enum
from functools import partial, reduce

from cls_cad_backend.database.commands import get_all_parts_for_project
from cls_cad_backend.util.hrid import generate_id
from cls_cad_backend.util.motion import combine_motions
from picls import Any, Arrow, Constructor, Omega, Subtypes, Type
from picls.dsl import DSL
from picls.types import Literal, TVar


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


def generate_leaf(provides: list[Constructor], part_counts, taxonomy) -> Type:
    arguments = [
        Literal(1, count_name)
        if taxonomy.check_subtype(
            Type.intersect(provides),
            Type.intersect([Constructor(type_name) for type_name in count_types]),
            dict(),
        )
        else Literal(0, count_name)
        for count_types, _, count_name in part_counts
    ]

    return Type.intersect(
        [Constructor(typ.name, wrapped_counted_types(arguments)) for typ in provides]
    )


def collect_and_increment_part_count(
    counted_vars: dict[str, Any], count_name: str, multiplicities: Mapping[str, int]
):
    return (
        sum(
            [
                v * multiplicities.get(k.partition("_")[0], 1)
                for k, v in counted_vars.items()
                if k.endswith(count_name)
            ]
        )
        + 1
    )


def collect_part_count(
    counted_vars: dict, count_name: str, multiplicities: Mapping[str, int]
):
    return sum(
        [
            v * multiplicities.get(k.partition("_")[0], 1)
            for k, v in counted_vars.items()
            if k.endswith(count_name)
        ]
    )


def get_joint_origin_type(
    uuid: str, part: dict, role: Role, prefix=""
) -> list[Constructor]:
    return [Constructor(f"{prefix}{tpe}") for tpe in part["jointOrigins"][uuid][role]]


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
            "name": "clsconnectmarker_" + str(hash(generate_id())),
            "forgeDocumentId": "NoInsert",
            "forgeFolderId": "NoInsert",
            "forgeProjectId": "NoInsert",
            "jointOrder": {},
            "provides": required_joint_origin_uuid,
            "motion": "Rigid",
        }
    )


def wrapped_counted_types(types: list[Type]) -> Type:
    return Type.intersect(
        [Constructor(f"counts_{i}", type) for i, type in enumerate(types)]
    )


def types_from_uuids(
    uuids: list, part: dict, prefix=""
) -> OrderedDict[str, list[Constructor]]:
    return OrderedDict(
        zip(
            uuids,
            [
                *[
                    get_joint_origin_type(x, part, Role.requires, prefix)
                    for x in uuids[:-1]
                ],
                *[get_joint_origin_type(uuids[-1], part, Role.provides, prefix)],
            ],
        )
    )


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
        part: dict,
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
            pass

            if is_blacklisted_under_subtyping(
                blacklist,
                configuration["providesJointOrigin"],
                part,
                taxonomy,
                Role.provides,
            ):
                continue

            types_by_uuid: dict[str, list[Constructor]] = types_from_uuids(
                [
                    *configuration["requiresJointOrigins"],
                    *[configuration["providesJointOrigin"]],
                ],
                part,
            )

            part_type = DSL()
            provides_type: Type = Omega()

            if len(types_by_uuid) == 1 and part_counts:
                provides_type = generate_leaf(
                    next(reversed(types_by_uuid.values())),
                    part_counts,
                    taxonomy,
                )
            elif len(types_by_uuid) > 1 and part_counts:
                provides_type = Type.intersect(next(reversed(types_by_uuid.values())))

                # We collect the count variables for each position, so that we can
                # annotate the constructor afterwards.
                counted_types: defaultdict[str, list[Type]] = defaultdict(list)
                multiplicities: dict[str, int] = {}

                for count_types, _, count_name in part_counts:
                    for uuid, joint_type in types_by_uuid.items():
                        part_type = part_type.Use(f"{uuid}_{count_name}", count_name)
                        counted_types[uuid].append(TVar(f"{uuid}_{count_name}"))
                        multiplicities[uuid] = part["jointOrigins"][uuid]["count"]

                    if taxonomy.check_subtype(
                        provides_type,
                        Type.intersect(
                            [Constructor(type_name) for type_name in count_types]
                        ),
                        dict(),
                    ):
                        part_type = part_type.AsRaw(
                            partial(
                                collect_and_increment_part_count,
                                count_name=count_name,
                                multiplicities=multiplicities,
                            )
                        )
                    else:
                        part_type = part_type.AsRaw(
                            partial(
                                collect_part_count,
                                count_name=count_name,
                                multiplicities=multiplicities,
                            )
                        )

                # Add the counts to the types of the joints origins
                types_with_count_by_uuid = OrderedDict(
                    zip(
                        types_by_uuid.keys(),
                        [
                            Type.intersect(
                                [
                                    Constructor(
                                        t.name,
                                        wrapped_counted_types(counted_types[uuid]),
                                    )
                                    for t in joint_types
                                ]
                            )
                            for uuid, joint_types in types_by_uuid.items()
                        ],
                    )
                )

                # Instead of a -> b -> c -> d, we now take Use(a).Use(b).Use(c).In(d)
                for uuid, joint_types in list(types_with_count_by_uuid.items())[:-1]:
                    part_type = part_type.Use(f"{uuid}", joint_types)
                provides_type = next(reversed(types_with_count_by_uuid.values()))
            else:
                for uuid, joint_types in list(types_by_uuid.items())[:-1]:
                    part_type.Use(
                        f"{uuid}",
                        Type.intersect(joint_types),
                    )
                provides_type = Type.intersect(next(reversed(types_by_uuid.values())))

            part_type = part_type.In(provides_type)

            repository[
                Part(
                    dict(
                        part["meta"],
                        requiredJointOriginsInfo=fetch_required_joint_origins_info(
                            part, configuration
                        ),
                        provides=configuration["providesJointOrigin"],
                        motion=fetch_joint_origin_info(
                            part, configuration["providesJointOrigin"]
                        )["motion"],
                    )
                )
            ] = part_type

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
                ] = get_joint_origin_type(
                    required_joint_origin_uuid, part, Role.requires
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
        for part in get_all_parts_for_project(project_id):
            RepositoryBuilder.add_part_to_repository(
                part,
                repository,
                part_counts=part_counts,
                blacklist=blacklist,
                connect_uuid=connect_uuid,
                taxonomy=taxonomy,
            )
        return repository
