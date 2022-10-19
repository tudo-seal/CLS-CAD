from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Type(ABC):
    is_omega: bool = field(init=True, kw_only=True, compare=False)
    size: int = field(init=True, kw_only=True, compare=False)
    organized: set["Type"] = field(init=True, kw_only=True, compare=False)
    path: tuple[list["Type"], "Type"] | None = field(
        init=True, kw_only=True, compare=False
    )

    def __str__(self) -> str:
        return self._str_prec(0)

    def __mul__(self, other: "Type") -> "Type":
        return Product(self, other)

    @abstractmethod
    def _path(self) -> tuple[list["Type"], "Type"] | None:
        pass

    @abstractmethod
    def _organized(self) -> set["Type"]:
        pass

    @abstractmethod
    def _size(self) -> int:
        pass

    @abstractmethod
    def _is_omega(self) -> bool:
        pass

    @abstractmethod
    def _str_prec(self, prec: int) -> str:
        pass

    @staticmethod
    def _parens(s: str) -> str:
        return f"({s})"

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

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["is_omega"]
        del state["size"]
        del state["organized"]
        del state["path"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.__dict__["is_omega"] = self._is_omega()
        self.__dict__["size"] = self._size()
        self.__dict__["path"] = self._path()
        self.__dict__["organized"] = self._organized()


@dataclass(frozen=True)
class Omega(Type):
    is_omega: bool = field(init=False, compare=False)
    size: bool = field(init=False, compare=False)
    organized: set[Type] = field(init=False, compare=False)
    path: tuple[list["Type"], "Type"] | None = field(init=False, compare=False)

    def __post_init__(self):
        super().__init__(
            is_omega=self._is_omega(),
            size=self._size(),
            organized=self._organized(),
            path=self._path(),
        )

    def _is_omega(self) -> bool:
        return True

    def _size(self) -> int:
        return 1

    def _path(self) -> tuple[list["Type"], "Type"] | None:
        return None

    def _organized(self) -> set["Type"]:
        return set()

    def _str_prec(self, prec: int) -> str:
        return "omega"


@dataclass(frozen=True)
class Constructor(Type):
    name: object = field(init=True)
    arg: Type = field(default=Omega(), init=True)
    is_omega: bool = field(init=False, compare=False)
    size: int = field(init=False, compare=False)
    organized: set[Type] = field(init=False, compare=False)
    path: tuple[list["Type"], "Type"] | None = field(init=False, compare=False)

    def __post_init__(self):
        super().__init__(
            is_omega=self._is_omega(),
            size=self._size(),
            organized=self._organized(),
            path=self._path(),
        )

    def _is_omega(self) -> bool:
        return False

    def _size(self) -> int:
        return 1 + self.arg.size

    def _path(self) -> tuple[list["Type"], "Type"] | None:
        return ([], self) if self.arg.path or self.arg == Omega() else None

    def _organized(self) -> set["Type"]:
        return (
            {self}
            if self._path()
            else set(map(lambda ap: Constructor(self.name, ap), self.arg.organized))
        )

    def _str_prec(self, prec: int) -> str:
        if self.arg == Omega():
            return str(self.name)
        else:
            return f"{str(self.name)}({str(self.arg)})"


@dataclass(frozen=True)
class Product(Type):
    left: Type = field(init=True)
    right: Type = field(init=True)
    is_omega: bool = field(init=False, compare=False)
    size: int = field(init=False, compare=False)
    organized: set[Type] = field(init=False, compare=False)
    path: tuple[list["Type"], "Type"] | None = field(init=False, compare=False)

    def __post_init__(self):
        super().__init__(
            is_omega=self._is_omega(),
            size=self._size(),
            organized=self._organized(),
            path=self._path(),
        )

    def _is_omega(self) -> bool:
        return False

    def _size(self) -> int:
        return 1 + self.left.size + self.right.size

    def _path(self) -> tuple[list["Type"], "Type"] | None:
        return (
            ([], self)
            if (
                (self.left == Omega() and self.right == Omega())
                or (self.left.path and self.right == Omega())
                or (self.left == Omega() and self.right.path)
            )
            else None
        )

    def _organized(self) -> set["Type"]:
        if self._path():
            return {self}
        else:
            return set.union(
                set(map(lambda lp: Product(lp, Omega()), self.left.organized)),
                set(map(lambda rp: Product(Omega(), rp), self.right.organized)),
            )

    def _str_prec(self, prec: int) -> str:
        product_prec: int = 9

        def product_str_prec(other: Type) -> str:
            match other:
                case Product(_, _):
                    return other._str_prec(product_prec)
                case _:
                    return other._str_prec(product_prec + 1)

        result: str = (
            f"{product_str_prec(self.left)} * {self.right._str_prec(product_prec + 1)}"
        )
        return Type._parens(result) if prec > product_prec else result


@dataclass(frozen=True)
class Arrow(Type):
    source: Type = field(init=True)
    target: Type = field(init=True)
    is_omega: bool = field(init=False, compare=False)
    size: int = field(init=False, compare=False)
    organized: set[Type] = field(init=False, compare=False)
    path: tuple[list["Type"], "Type"] | None = field(init=False, compare=False)

    def __post_init__(self):
        super().__init__(
            is_omega=self._is_omega(),
            size=self._size(),
            organized=self._organized(),
            path=self._path(),
        )

    def _is_omega(self) -> bool:
        return self.target.is_omega

    def _size(self) -> int:
        return 1 + self.source.size + self.target.size

    def _path(self) -> tuple[list["Type"], "Type"] | None:
        return (
            ([self.source, *(self.target.path[0])], self.target.path[1])
            if self.target.path
            else None
        )

    def _organized(self) -> set["Type"]:
        return (
            {self}
            if self._path()
            else set(map(lambda tp: Arrow(self.source, tp), self.target.organized))
        )

    def _str_prec(self, prec: int) -> str:
        arrow_prec: int = 8
        result: str
        match self.target:
            case Arrow(_, _):
                result = f"{self.source._str_prec(arrow_prec + 1)} -> {self.target._str_prec(arrow_prec)}"
            case _:
                result = f"{self.source._str_prec(arrow_prec + 1)} -> {self.target._str_prec(arrow_prec + 1)}"
        return Type._parens(result) if prec > arrow_prec else result


@dataclass(frozen=True)
class Intersection(Type):
    left: Type = field(init=True)
    right: Type = field(init=True)
    is_omega: bool = field(init=False, compare=False)
    size: int = field(init=False, compare=False)
    organized: set[Type] = field(init=False, compare=False)
    path: tuple[list["Type"], "Type"] | None = field(init=False, compare=False)

    def __post_init__(self):
        super().__init__(
            is_omega=self._is_omega(),
            size=self._size(),
            organized=self._organized(),
            path=self._path(),
        )

    def _is_omega(self) -> bool:
        return self.left.is_omega and self.right.is_omega

    def _size(self) -> int:
        return 1 + self.left.size + self.right.size

    def _path(self) -> tuple[list["Type"], "Type"] | None:
        return None

    def _organized(self) -> set["Type"]:
        return set.union(self.left.organized, self.right.organized)

    def _str_prec(self, prec: int) -> str:
        intersection_prec: int = 10

        def intersection_str_prec(other: Type) -> str:
            match other:
                case Intersection(_, _):
                    return other._str_prec(intersection_prec)
                case _:
                    return other._str_prec(intersection_prec + 1)

        result: str = (
            f"{intersection_str_prec(self.left)} & {intersection_str_prec(self.right)}"
        )
        return Type._parens(result) if prec > intersection_prec else result
