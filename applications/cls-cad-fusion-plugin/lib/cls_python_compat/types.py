from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Type(ABC):
    @staticmethod
    def intersect(types: Sequence["Type"]) -> "Type":
        if len(types) > 0:
            rtypes = reversed(types)
            result: "Type" = next(rtypes)
            for ty in rtypes:
                result = Intersection(ty, result)
            return result
        else:
            return Omega()


@dataclass(frozen=True)
class Omega(Type):
    pass


@dataclass(frozen=True)
class Constructor(Type):
    name: object = field(init=True)
    arg: Type = field(default=Omega(), init=True)


@dataclass(frozen=True)
class Product(Type):
    left: Type = field(init=True)
    right: Type = field(init=True)


@dataclass(frozen=True)
class Arrow(Type):
    source: Type = field(init=True)
    target: Type = field(init=True)


@dataclass(frozen=True)
class Intersection(Type):
    left: Type = field(init=True)
    right: Type = field(init=True)
