import json
from collections import OrderedDict, defaultdict
from collections.abc import Mapping
from enum import Enum
from functools import partial

from cls_cad_backend.database.commands import get_all_parts_for_project
from cls_cad_backend.util.motion import combine_motions
from clsp import Any, Constructor, Omega, Subtypes, Type
from clsp.dsl import DSL
from clsp.types import Literal, LVar


class Part:
    def __call__(self, *required_parts):
        """
        Collects all arguments that the term gives to a specific application. Then,
        recursively interprets these into a dict that matches the later Fusion 360
        assembly tree.

        :param required_parts: The set of all parts connected to this part.
        :return: The completed dictionary of this part.
        """
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

    def __hash__(self):
        """
        Necessary for clsp to distinguish Part objects in the repository.

        :return: A hash dependent on the Part JSON.
        """
        return hash(json.dumps(self.info))

    def __init__(self, info) -> None:
        """
        Parts get created with info from their JSON representation. This is aggregated
        in the call method.

        :param info: A dict containing information about the part.
        """
        self.info = info

    def __eq__(self, other):
        """
        Required for clsp. Computes equality based on if two parts have exactly the
        same info dict.

        :param other: The object to compare against.
        :return: true if the objects are equal, else false.
        """
        return isinstance(other, Part) and self.__hash__() == other.__hash__()


class Role(str, Enum):
    requires = "requires"
    provides = "provides"


def generate_leaf(provides: list[Constructor], part_counts, taxonomy) -> Type:
    """
    Generates a leaf type, i.e., the type of a part that only provides something and
    doesn't require anything. Such a part binds either a part count of 0 or 1 of a
    counted Literal, depending on if it is a subtype of the counted metric or not.

    :param provides: A list of constructors that when intersected represent the provided
        type.
    :param part_counts: The set of constraints.
    :param taxonomy: The taxonomy that decides if the part provides 1 or 0 of a
        constraint.
    :return: The complete type of the leaf part.
    """
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
    """
    Collect the part counts of all positions in the multi-arrow type and compute their
    sum, incremented by one.

    :param counted_vars: The set of Literals that are bound by clsp.
    :param count_name: The name of the Literal that will be bound to the result.
    :param multiplicities: An optional set of multiplicities, signalling that a type
        corresponds to multiple physical.
    :return: The sum of the weighted individual part counts.
    """
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
    """
    Collect the part counts of all positions in the multi-arrow type and compute their
    sum.

    :param counted_vars: The set of Literals that are bound by clsp.
    :param count_name: The name of the Literal that will be bound to the result.
    :param multiplicities: An optional set of multiplicities, signalling that a type
        corresponds to multiple physical.
    :return: The sum of the weighted individual part counts.
    """
    return sum(
        [
            v * multiplicities.get(k.partition("_")[0], 1)
            for k, v in counted_vars.items()
            if k.endswith(count_name)
        ]
    )


def get_joint_origin_type(
    uuid: str, part: dict, role: Role, prefix: str = ""
) -> list[Constructor]:
    """
    Convert the type information for a specific JointOrigin in a part JSON to actual
    type constructors.

    :param uuid: The uuid of the JointOrigin to create constructors for.
    :param part: The part JSON containing information on the JointOrigin.
    :param role: Either "Requires" or "Provides", the corresponding types are built.
    :param prefix: An optional prefix for the constructor.
    :return: A list of Constructors that when intersected type the JointOrigin.
    """
    return [Constructor(f"{prefix}{tpe}") for tpe in part["jointOrigins"][uuid][role]]


def fetch_required_joint_origins_info(part, configuration):
    """
    Retrieve the subsets of the part JSON relevant to the JointOrigin uuids of a
    configuration of the part. A configuration is one joint being selected as provided
    and all others as required.

    :param part: The complete part JSON.
    :param configuration: The configuration to retrieve information for.
    :return: A list of the JSON subsets pertaining to the JointOrigins in the
        configuration.
    """
    return {
        joint_origin_uuid: fetch_joint_origin_info(part, joint_origin_uuid)
        for joint_origin_uuid in configuration["requiresJointOrigins"]
    }


def fetch_joint_origin_info(part, joint_origin_uuid: str):
    """
    Retrieve the subset of the part JSON relevant to a specific JointOrigin uuid.

    :param part: The complete part JSON.
    :param joint_origin_uuid: The uuid to retrieve a subset for.
    :return: The subset of the JSON for given uuid.
    """
    return part["jointOrigins"][joint_origin_uuid]


def wrapped_counted_types(types: list[Type]) -> Type:
    """
    Takes a list of types and wraps them in Constructors.

    :param types: The list of types to wrap.
    :return: The list of wrapped types.
    """
    return Type.intersect(
        [Constructor(f"counts_{i}", type) for i, type in enumerate(types)]
    )


def types_from_uuids(
    uuids: list, part: dict, prefix: str = ""
) -> OrderedDict[str, list[Constructor]]:
    """
    Given a JSON of a part and a list of JointOrigin uuids, return a list of tuples of
    uuid and corresponding type information.

    :param uuids: A list of uuids to retrieve type information for.
    :param part: The part JSON that contains all the uuids.
    :param prefix: An optional prefix for the constructor types.
    :return: The list of tuples of uuid and corresponding type.
    """
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


class RepositoryBuilder:
    @staticmethod
    def add_part_to_repository(
        part: dict,
        repository: dict,
        *,
        part_counts: list[tuple[str, int, str]] | None = None,
        taxonomy: Subtypes = None,
    ) -> None:
        """
        Adds a part to a repository to be used for synthesis. The type is dependent on
        the constraints in part_counts. If no part_counts are provided, the generated
        types are multi-arrows where each position is the type of the respective
        JointOrigin, terminating in the provided type of the provided JointOrigin.

        :param part_counts: The constraints the type needs to account for, i.e. add
            Literals that get incremented.
        :param part: The JSON representation of the part to add to the repository.
        :param repository: The repository dict for the part to be added to.
        :param taxonomy: The taxonomy to check against if a type needs to increment a
            Literal or not.
        :return:
        """
        for configuration in part["configurations"]:
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
                    for uuid, _ in types_by_uuid.items():
                        part_type = part_type.Use(f"{uuid}_{count_name}", count_name)
                        counted_types[uuid].append(LVar(f"{uuid}_{count_name}"))
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

    @staticmethod
    def add_all_to_repository(
        project_id: str,
        taxonomy: Subtypes,
        *,
        part_counts: list[tuple[str, int, str]] | None = None,
    ):
        """
        Add all parts found in the database from a specific project into the repository.

        :param project_id: The id of the project to get parts from.
        :param taxonomy: The taxonomy describing the subtype relationships.
        :param part_counts: The constraints for the synthesis request (the types in the
            repository depend on this).
        :return: The repository containing all part combinators with their respective
            types.
        """
        repository: dict = {}
        for part in get_all_parts_for_project(project_id):
            RepositoryBuilder.add_part_to_repository(
                part,
                repository,
                part_counts=part_counts,
                taxonomy=taxonomy,
            )
        return repository
