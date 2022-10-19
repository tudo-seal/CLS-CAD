from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Callable, Iterable, Iterator, Sequence
from typing import Generic, NoReturn, SupportsIndex, Tuple, TypeVar, Union, overload

A = TypeVar("A", covariant=True)
B = TypeVar("B", covariant=True)
C = TypeVar("C")


class ComputationStep(Iterable["ComputationStep"], ABC):
    @abstractmethod
    def __iter__(self) -> Iterator["ComputationStep"]:
        pass

    def run(self) -> None:
        steps: deque[Iterator[ComputationStep]] = deque([iter(self)])
        while steps:
            head = steps.popleft()
            try:
                head_step = next(head)
                steps.appendleft(head)
                steps.appendleft(iter(head_step))
            except StopIteration:
                pass


class EmptyStep(ComputationStep):
    def __iter__(self) -> Iterator["ComputationStep"]:
        return
        yield self


class Finite(Sequence[A], ABC):
    def __init__(self):
        self.cache: dict[int, A] = dict()
        self._size = -1

    @staticmethod
    def empty() -> "Finite[C]":
        return FiniteEmpty()

    @staticmethod
    def singleton(value: C) -> "Finite[C]":
        return FiniteSingleton(value)

    @staticmethod
    def lazy_singleton(value: Callable[[], C]) -> "Finite[C]":
        return FiniteLazySingleton(value)

    @staticmethod
    def of(seq: Sequence[C]) -> "Finite[C]":
        return FiniteOfSequence(seq)

    def _add_opt(self, other: "Finite[C]") -> "Finite[Union[C, A]]":
        return FiniteUnion(other, self)

    def __add__(self, other: "Finite[C]") -> "Finite[Union[A, C]]":
        return other._add_opt(self)

    def _mul_opt(self, other: "Finite[C]") -> "Finite[Tuple[C, A]]":
        return FiniteProduct(other, self)

    def __mul__(self, other: "Finite[C]") -> "Finite[Tuple[A, C]]":
        return other._mul_opt(self)

    def map(self, f: Callable[[A], C]) -> "Finite[C]":
        return FiniteMap(self, f)

    def __len__(self):
        return self.size

    @overload
    def __getitem__(self, index: int) -> A:
        ...

    @overload
    def __getitem__(self, index: SupportsIndex) -> A:
        ...

    @overload
    def __getitem__(self, index: slice) -> "Finite[A]":
        ...

    def __getitem__(self, index: int | SupportsIndex | slice) -> Union[A, "Finite[A]"]:
        def int_case(index: int) -> A:
            if index < 0 or index >= self.size:
                raise IndexError(index)
            return self.get_checked(index)

        if isinstance(index, int):
            return int_case(index)
        elif isinstance(index, SupportsIndex):
            return int_case(index.__index__())
        else:
            return FiniteSlice(self, index)

    @abstractmethod
    def size_computation(self) -> ComputationStep:
        pass

    @abstractmethod
    def computation(self, index: int) -> ComputationStep:
        pass

    @property
    def size(self) -> int:
        if self._size < 0:
            self.size_computation().run()
        return self._size

    @size.setter
    def size(self, value: int) -> None:
        self._size = value

    def cached_size_computation(self) -> ComputationStep:
        if self._size >= 0:
            return EmptyStep()
        else:
            return self.size_computation()

    def cached_computation(self, index: int) -> ComputationStep:
        if index in self.cache:
            return EmptyStep()
        else:
            return self.computation(index)

    def get_checked(self, index: int) -> A:
        if index not in self.cache:
            self.computation(index).run()
        return self.cache[index]

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "Finite[A]"):
            self.outer: "Finite[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            self.outer.cache = dict()
            self.outer._size = -1
            yield EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    def clear_cache(self) -> None:
        self.clear_cache_computation().run()


class FiniteEmpty(Finite[NoReturn]):
    def __init__(self):
        super().__init__()
        self.size = 0

    def size_computation(self) -> ComputationStep:
        return EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return EmptyStep()

    def _mul_opt(self, other: "Finite[C]") -> "Finite[Tuple[C, A]]":
        return self

    def __mul__(self, other):
        return self

    def _add_opt(self, other: "Finite[C]") -> "Finite[Union[C, A]]":
        return other

    def __add__(self, other):
        return other

    def pay(self):
        return self

    def map(self, f: Callable[[A], C]) -> "Finite[C]":
        return self


class FiniteSingleton(Finite[A]):
    def __init__(self, value: A):
        super().__init__()
        self.value = value
        self.cache[0] = value
        self.size = 1

    def size_computation(self) -> ComputationStep:
        return EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return EmptyStep()

    def _mul_opt(self, other: "Finite[C]") -> "Finite[Tuple[C, A]]":
        def g(_x):
            return (_x, self.value)

        return other.map(g)

    def __mul__(self, other):
        def g(_x):
            return (self.value, _x)

        return other.map(g)

    def map(self, f: Callable[[A], C]) -> "Finite[C]":
        return FiniteSingleton(f(self.value))


class FiniteLazySingleton(Finite[A]):
    def __init__(self, value: Callable[[], A]):
        super().__init__()
        self.value: Callable[[], A] = value
        self.size = 1

    def size_computation(self) -> ComputationStep:
        return EmptyStep()

    class SingletonComputation(ComputationStep):
        def __init__(self, outer: "FiniteLazySingleton[A]"):
            self.outer: "FiniteLazySingleton[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            self.outer.cache[0] = self.outer.value()
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.SingletonComputation(self)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "Finite[A]"):
            self.outer: "Finite[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            self.outer.cache = dict()
            yield EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)


class FiniteOfSequence(Finite[A]):
    def __init__(self, seq: Sequence[A]):
        super().__init__()
        self.seq: Sequence[A] = seq

    class SizeComputation(ComputationStep):
        def __init__(self, outer: "FiniteOfSequence[A]"):
            self.outer: "FiniteOfSequence[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            self.outer.size = len(self.outer.seq)
            yield EmptyStep()

    def size_computation(self) -> ComputationStep:
        return self.SizeComputation(self)

    class SequenceComputation(ComputationStep):
        def __init__(self, outer: "FiniteOfSequence[A]", index: int):
            self.outer: "FiniteOfSequence[A]" = outer
            self.index = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index
            if index not in self.outer.cache:
                self.outer.cache[index] = self.outer.seq[index]
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.SequenceComputation(self, index)


class FiniteSlice(Finite[A]):
    def __init__(self, over: "Finite[A]", s: slice):
        super().__init__()
        self.over: Finite[A] = over
        self.s: slice = s

    class SizeComputation(ComputationStep):
        def __init__(self, outer: "FiniteSlice[A]"):
            self.outer: "FiniteSlice[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            s = self.outer.s
            start: int = s.start if s.start else 0
            step: int = s.step if s.step else 1
            stop: int = s.stop
            self.outer.size = (stop - start) // step
            yield EmptyStep()

    def size_computation(self) -> ComputationStep:
        return self.SizeComputation(self)

    class SliceComputation(ComputationStep):
        def __init__(self, outer: "FiniteSlice[A]", index: int):
            self.outer: "FiniteSlice[A]" = outer
            self.index: int = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index = self.index
            s = self.outer.s
            start: int = s.start if s.start else 0
            step: int = s.step if s.step else 1
            outer_index = start + index * step
            yield self.outer.over.cached_computation(outer_index)
            self.outer.cache[index] = self.outer.over.get_checked(outer_index)
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.SliceComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "FiniteSlice[A]"):
            self.outer: "FiniteSlice[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.over.clear_cache_computation()
            yield Finite[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)


class FiniteUnion(Finite[A]):
    def __init__(self, left: Finite[A], right: Finite[A]):
        super().__init__()
        self.left: Finite[A] = left
        self.right: Finite[A] = right

    class SizeComputation(ComputationStep):
        def __init__(self, outer: "FiniteUnion[A]"):
            self.outer: "FiniteUnion[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.left.cached_size_computation()
            yield self.outer.right.cached_size_computation()
            self.outer.size = self.outer.left.size + self.outer.right.size
            yield EmptyStep()

    def size_computation(self) -> ComputationStep:
        return self.SizeComputation(self)

    class UnionComputation(ComputationStep):
        def __init__(self, outer: "FiniteUnion[A]", index: int):
            self.outer: "FiniteUnion[A]" = outer
            self.index: int = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index = self.index
            yield self.outer.left.cached_size_computation()
            left_size = self.outer.left.size
            if index < left_size:
                yield self.outer.left.cached_computation(index)
                self.outer.cache[index] = self.outer.left.get_checked(index)
            else:
                yield self.outer.right.cached_computation(index - left_size)
                self.outer.cache[index] = self.outer.right.get_checked(
                    index - left_size
                )
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.UnionComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "FiniteUnion[A]"):
            self.outer: "FiniteUnion[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.left.clear_cache_computation()
            yield self.outer.right.clear_cache_computation()
            yield Finite[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)


class FiniteProduct(Finite[tuple[A, B]], Generic[A, B]):
    def __init__(self, left: Finite[A], right: Finite[B]):
        super().__init__()
        self.left: Finite[A] = left
        self.right: Finite[B] = right

    class SizeComputation(ComputationStep):
        def __init__(self, outer: "FiniteProduct[A, B]"):
            self.outer: "FiniteProduct[A, B]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.left.cached_size_computation()
            yield self.outer.right.cached_size_computation()
            self.outer.size = self.outer.left.size * self.outer.right.size
            yield EmptyStep()

    def size_computation(self) -> ComputationStep:
        return self.SizeComputation(self)

    class ProductComputation(ComputationStep):
        def __init__(self, outer: "FiniteProduct[A, B]", index: int):
            self.outer: "FiniteProduct[A, B]" = outer
            self.index: int = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index
            yield self.outer.right.size_computation()
            size: int = self.outer.right.size
            yield self.outer.left.cached_computation(index // size)
            yield self.outer.right.cached_computation(index % size)
            self.outer.cache[index] = (
                self.outer.left.get_checked(index // size),
                self.outer.right.get_checked(index % size),
            )
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.ProductComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "FiniteProduct[A, B]"):
            self.outer: "FiniteProduct[A, B]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.left.clear_cache_computation()
            yield self.outer.right.clear_cache_computation()
            yield Finite[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)


class FiniteMap(Finite[A], Generic[C, A]):
    def __init__(self, over: "Finite[C]", f: Callable[[C], A]):
        super().__init__()
        self.over: Finite[C] = over
        self.f: Callable[[C], A] = f

    class SizeComputation(ComputationStep):
        def __init__(self, outer: "FiniteMap[C, A]"):
            self.outer: "FiniteMap[C, A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.over.cached_size_computation()
            self.outer.size = self.outer.over.size
            yield EmptyStep()

    def size_computation(self) -> ComputationStep:
        return self.SizeComputation(self)

    class MapComputation(ComputationStep):
        def __init__(self, outer: "FiniteMap[C, A]", index: int):
            self.outer: "FiniteMap[C, A]" = outer
            self.index: int = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index = self.index
            yield self.outer.over.cached_computation(index)
            self.outer.cache[index] = self.outer.f(self.outer.over.get_checked(index))
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.MapComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "FiniteMap[C, A]"):
            self.outer: "FiniteMap[C, A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.over.clear_cache_computation()
            yield Finite[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    def map(self, f: Callable[[A], C]) -> "Finite[C]":
        def g(x):
            return f(self.f(x))

        return FiniteMap(self.over, g)


class Enumeration(Iterable[A], ABC):
    def __init__(self):
        self.cache: dict[int, Finite[A]] = dict()
        self.max_size: int = -1

    @staticmethod
    def empty() -> "Enumeration[C]":
        return EnumerationEmpty()

    @staticmethod
    def singleton(value: C) -> "Enumeration[C]":
        return EnumerationSingleton(value)

    @staticmethod
    def lazy_singleton(value: Callable[[], C]) -> "Enumeration[C]":
        return EnumerationLazySingleton(value)

    @staticmethod
    def of(iterable: Iterable[C]) -> "Enumeration[C]":
        return EnumerationOfIterable(iterable)

    @staticmethod
    def lazy(factory: Callable[[], "Enumeration[C]"]) -> "Enumeration[C]":
        return EnumerationLazy(factory)

    @staticmethod
    def ints() -> "Enumeration[int]":
        def inf() -> Iterator[int]:
            x: int = 0
            while True:
                yield x
                x = x + 1

        return Enumeration.of(inf())

    def _add_opt(self, other: "Enumeration[C]") -> "Enumeration[Union[C, A]]":
        return EnumerationUnion(other, self)

    def __add__(self, other: "Enumeration[C]") -> "Enumeration[Union[A, C]]":
        return other._add_opt(self)

    def _mul_opt(self, other: "Enumeration[C]") -> "Enumeration[Tuple[C, A]]":
        return EnumerationProduct(other, self)

    def __mul__(self, other: "Enumeration[C]") -> "Enumeration[Tuple[A, C]]":
        return other._mul_opt(self)

    def pay(self) -> "Enumeration[A]":
        return EnumerationPay(self)

    def map(self, f: Callable[[A], C]) -> "Enumeration[C]":
        return EnumerationMap(self, f)

    def __iter__(self) -> Iterator[A]:
        pos: int = 0
        while True:
            part = self.get_values(pos)
            yield from part
            pos += 1

    @overload
    def __getitem__(self, index: int) -> A:
        ...

    @overload
    def __getitem__(self, index: SupportsIndex) -> A:
        ...

    @overload
    def __getitem__(self, index: slice) -> "Finite[A]":
        ...

    def __getitem__(self, index: int | SupportsIndex | slice) -> Union[A, "Finite[A]"]:
        def int_case(index: int) -> A:
            items = self.all_values()
            while True:
                try:
                    part = next(items)
                    part_len: int = len(part)
                    if index < part_len:
                        return part[index]
                    else:
                        index -= part_len
                except StopIteration:
                    raise IndexError(index)

        if isinstance(index, int):
            return int_case(index)
        elif isinstance(index, SupportsIndex):
            return int_case(index.__index__())
        else:
            return EnumerationSlice(self, index)

    @abstractmethod
    def computation(self, index: int) -> ComputationStep:
        pass

    def cached_computation(self, index: int) -> ComputationStep:
        if index in self.cache:
            return EmptyStep()
        else:
            return self.computation(index)

    def all_values(self) -> Iterator[A]:
        pos: int = 0
        while True:
            yield self.get_values(pos)
            pos += 1

    def get_values(self, index: int) -> Finite[A]:
        if index not in self.cache:
            self.computation(index).run()
        return self.cache[index]

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "Enumeration[A]"):
            self.outer: "Enumeration[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            for entry in self.outer.cache.values():
                yield entry.clear_cache_computation()
            self.outer.cache = dict()
            self.outer.max_size = -1
            yield EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    def clear_cache(self) -> None:
        self.clear_cache_computation().run()

    @abstractmethod
    def max_size_computation(self) -> ComputationStep:
        pass

    def cached_max_size_computation(self) -> ComputationStep:
        if self.max_size >= 0:
            return EmptyStep()
        else:
            return self.max_size_computation()

    def unsafe_max_size(self) -> int | NoReturn:
        if self.max_size < 0:
            self.max_size_computation().run()
        return self.max_size


class EnumerationEmpty(Enumeration[NoReturn]):
    def __init__(self):
        super().__init__()
        self.empty: Finite[A] = Finite.empty()
        self.max_size = 0

    def get_values(self, index: int) -> Finite[A]:
        return self.empty

    def computation(self, index: int) -> ComputationStep:
        return EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return EmptyStep()

    def clear_cache(self) -> None:
        pass

    def _add_opt(self, other: "Enumeration[C]") -> "Enumeration[Union[C, A]]":
        return other

    def __add__(self, other):
        return other

    def _mul_opt(self, other: "Enumeration[C]") -> "Enumeration[Tuple[C, A]]":
        return self

    def __mul__(self, other):
        return self

    def pay(self):
        return self

    def map(self, f: Callable[[A], C]) -> "Enumeration[C]":
        return self

    def max_size_computation(self) -> ComputationStep:
        return EmptyStep()


class EnumerationSingleton(Enumeration[A]):
    def __init__(self, value: A):
        super().__init__()
        self.value = value
        self.empty: Finite[A] = Finite.empty()
        self.max_size = 1

    class SingletonComputation(ComputationStep):
        def __init__(self, outer: "EnumerationSingleton[A]", index: int):
            self.outer: "EnumerationSingleton[A]" = outer
            self.index = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index
            if index == 0:
                self.outer.cache[0] = Finite.singleton(self.outer.value)
            yield EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return EmptyStep()

    def clear_cache(self) -> None:
        pass

    def computation(self, index: int) -> ComputationStep:
        return self.SingletonComputation(self, index)

    def get_values(self, index: int) -> Finite[A]:
        if index > 0:
            return self.empty
        else:
            self.cached_computation(index).run()
            return self.cache[index]

    def _mul_opt(self, other: "Enumeration[C]") -> "Enumeration[Tuple[C, A]]":
        return other.map(lambda x: (x, self.value))

    def __mul__(self, other):
        return other.map(lambda x: (self.value, x))

    def map(self, f: Callable[[A], C]) -> "Enumeration[C]":
        return EnumerationSingleton(f(self.value))

    def max_size_computation(self) -> ComputationStep:
        return EmptyStep()


class EnumerationLazySingleton(Enumeration[A]):
    def __init__(self, value: Callable[[], A]):
        super().__init__()
        self.value: Callable[[], A] = value
        self.empty: Finite[A] = Finite.empty()
        self.max_size = 1

    class LazySingletonComputation(ComputationStep):
        def __init__(self, outer: "EnumerationLazySingleton[A]", index: int):
            self.outer: "EnumerationLazySingleton[A]" = outer
            self.index = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index
            if index == 0:
                self.outer.cache[0] = Finite.lazy_singleton(self.outer.value)
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.LazySingletonComputation(self, index)

    def get_values(self, index: int) -> Finite[A]:
        if index > 0:
            return self.empty
        else:
            if 0 not in self.cache:
                self.cached_computation(index).run()
            return self.cache[index]

    def max_size_computation(self) -> ComputationStep:
        return EmptyStep()

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationLazySingleton[A]"):
            self.outer: "EnumerationLazySingleton[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield Enumeration[A].clear_cache_computation(self.outer)
            self.outer.max_size = 1
            yield EmptyStep()

    def clear_cache_computation(self) -> ComputationStep:
        return LocalClearCacheComputation()


class EnumerationUnion(Enumeration[A]):
    def __init__(self, left: Enumeration[A], right: Enumeration[A]):
        super().__init__()
        self.left: Enumeration[A] = left
        self.right: Enumeration[A] = right

    class UnionComputation(ComputationStep):
        def __init__(self, outer: "EnumerationUnion[A]", index: int):
            self.outer: "EnumerationUnion[A]" = outer
            self.index: int = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index
            yield self.outer.left.cached_computation(index)
            yield self.outer.right.cached_computation(index)
            self.outer.cache[index] = self.outer.left.get_values(
                index
            ) + self.outer.right.get_values(index)
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.UnionComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationUnion[A]"):
            self.outer: "EnumerationUnion[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.left.clear_cache_computation()
            yield self.outer.right.clear_cache_computation()
            yield Enumeration[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    class MaxSizeComputation(ComputationStep):
        def __init__(self, outer: "EnumerationUnion[A]"):
            self.outer: "EnumerationUnion[A]" = outer

        def __iter__(self):
            yield self.outer.left.cached_max_size_computation()
            yield self.outer.right.cached_max_size_computation()
            self.outer.max_size = max(
                self.outer.left.unsafe_max_size(), self.outer.right.unsafe_max_size()
            )
            yield EmptyStep()

    def max_size_computation(self) -> ComputationStep:
        return self.MaxSizeComputation(self)


class EnumerationProduct(Enumeration[tuple[A, B]], Generic[A, B]):
    def __init__(self, left: Enumeration[A], right: Enumeration[B]):
        super().__init__()
        self.left: Enumeration[A] = left
        self.right: Enumeration[B] = right

    class ProductComputation(ComputationStep):
        def __init__(self, outer: "EnumerationProduct[A, B]", index: int):
            self.outer: "EnumerationProduct[A, B]" = outer
            self.index: int = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index

            result: Finite[tuple[A, B]] = Finite.empty()
            for left_index in range(0, index + 1):
                yield self.outer.left.cached_computation(left_index)
                right_index = index - left_index
                yield self.outer.right.cached_computation(right_index)
                result = result + (
                    self.outer.left.get_values(left_index)
                    * self.outer.right.get_values(right_index)
                )
            self.outer.cache[index] = result
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.ProductComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationProduct[A, B]"):
            self.outer: "EnumerationProduct[A, B]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.left.clear_cache_computation()
            yield self.outer.right.clear_cache_computation()
            yield Enumeration[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    class MaxSizeComputation(ComputationStep):
        def __init__(self, outer: "EnumerationProduct[A]"):
            self.outer: "EnumerationProduct[A, B]" = outer

        def __iter__(self):
            yield self.outer.left.cached_max_size_computation()
            yield self.outer.right.cached_max_size_computation()
            self.outer.max_size = (
                self.outer.left.unsafe_max_size() + self.outer.right.unsafe_max_size()
            )
            yield EmptyStep()

    def max_size_computation(self) -> ComputationStep:
        return self.MaxSizeComputation(self)


class EnumerationPay(Enumeration[A]):
    def __init__(self, other: Enumeration[A]):
        super().__init__()
        self.other: Enumeration[A] = other

    class PayComputation(ComputationStep):
        def __init__(self, outer: "EnumerationPay[A]", index: int):
            self.outer: "EnumerationPay[A]" = outer
            self.index = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index
            if index > 0:
                yield self.outer.other.cached_computation(index - 1)
                self.outer.cache[index] = self.outer.other.get_values(index - 1)
            else:
                self.outer.cache[0] = Finite.empty()
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.PayComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationPay[A]"):
            self.outer: "EnumerationPay[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.other.clear_cache_computation()
            yield Enumeration[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    class MaxSizeComputation(ComputationStep):
        def __init__(self, outer: "EnumerationPay[A]"):
            self.outer: "EnumerationPay[A]" = outer

        def __iter__(self):
            yield self.outer.other.cached_max_size_computation()
            self.outer.max_size = 1 + self.outer.other.unsafe_max_size()
            yield EmptyStep()

    def max_size_computation(self) -> ComputationStep:
        return self.MaxSizeComputation(self)


class EnumerationOfIterable(Enumeration[A]):
    def __init__(self, iterable: Iterable[A]):
        super().__init__()
        self.iterable: Iterable[A] = iterable
        self.state: tuple[bool, int, Iterator[A]] | None = None

    class IterableComputation(ComputationStep):
        def __init__(self, outer: "EnumerationOfIterable[A]", index: int):
            self.outer: "EnumerationOfIterable[A]" = outer
            self.index = index

        def __iter__(self) -> Iterator[ComputationStep]:
            if not self.outer.state:
                self.outer.state = (False, 0, iter(self.outer.iterable))
            index: int = self.index
            stopped, position, value_iter = self.outer.state
            while position <= index:
                if not stopped:
                    try:
                        elem = next(value_iter)
                        self.outer.cache[position] = Finite.singleton(elem)
                    except StopIteration:
                        self.outer.max_size = position - 1
                        self.outer.cache[position] = Finite.empty()
                        stopped = True
                else:
                    self.outer.cache[position] = Finite.empty()
                position += 1
                self.outer.state = (stopped, position, value_iter)
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.IterableComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationOfIterable[A]"):
            self.outer: "EnumerationOfIterable[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            self.outer.state = None
            yield Enumeration[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    class MaxSizeComputation(ComputationStep):
        def __init__(self, outer: "EnumerationOfIterable[A]"):
            self.outer: "EnumerationOfIterable[A]" = outer

        def __iter__(self):
            while self.outer.max_size < 0:
                yield self.outer.cached_computation(self.outer.state[1])
            yield EmptyStep()

    def max_size_computation(self) -> ComputationStep:
        return self.MaxSizeComputation(self)


class EnumerationLazy(Enumeration[A]):
    def __init__(self, factory: Callable[[], Enumeration[A]]):
        super().__init__()
        self.factory: Callable[[], Enumeration[A]] = factory
        self.value: Enumeration[A] | None = None

    class LazyComputation(ComputationStep):
        def __init__(self, outer: "EnumerationLazy[A]", index: int):
            self.outer: "EnumerationLazy[A]" = outer
            self.index = index

        def __iter__(self) -> Iterator[ComputationStep]:
            if not self.outer.value:
                self.outer.value = self.outer.factory()
            yield self.outer.value.cached_computation(self.index)
            self.outer.cache[self.index] = self.outer.value.get_values(self.index)

    def computation(self, index: int) -> ComputationStep:
        return self.LazyComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationLazy[A]"):
            self.outer: "EnumerationLazy[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            if self.outer.value:
                yield self.outer.value.clear_cache_computation()
            self.outer.cache = dict()
            self.outer.value = None
            yield Enumeration[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    class MaxSizeComputation(ComputationStep):
        def __init__(self, outer: "EnumerationLazy[A]"):
            self.outer: "EnumerationLazy[A]" = outer

        def __iter__(self):
            if not self.outer.value:
                self.outer.value = self.outer.factory()
            yield self.outer.value.cached_max_size_computation()
            self.outer.max_size = self.outer.value.unsafe_max_size()
            yield EmptyStep()

    def max_size_computation(self) -> ComputationStep:
        return self.MaxSizeComputation(self)


class EnumerationMap(Enumeration[A], Generic[C, A]):
    def __init__(self, over: Enumeration[C], f: Callable[[C], A]):
        super().__init__()
        self.over: Enumeration[C] = over
        self.f: Callable[[C], A] = f

    class MapComputation(ComputationStep):
        def __init__(self, outer: "EnumerationMap[C, A]", index: int):
            self.outer: "EnumerationMap[C, A]" = outer
            self.index = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index: int = self.index
            yield self.outer.over.cached_computation(index)
            self.outer.cache[index] = self.outer.over.get_values(index).map(
                self.outer.f
            )
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.MapComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationMap[C, A]"):
            self.outer: "EnumerationMap[C, A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.over.clear_cache_computation()
            yield Enumeration[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)

    def map(self, f: Callable[[A], C]) -> "Enumeration[C]":
        def g(x):
            return f(self.f(x))

        return EnumerationMap(self.over, g)

    class MaxSizeComputation(ComputationStep):
        def __init__(self, outer: "EnumerationMap[C, A]"):
            self.outer: "EnumerationMap[C, A]" = outer

        def __iter__(self):
            yield self.outer.over.cached_max_size_computation()
            self.outer.max_size = self.outer.over.unsafe_max_size()
            yield EmptyStep()

    def max_size_computation(self) -> ComputationStep:
        return self.MaxSizeComputation(self)


class EnumerationSlice(Finite[A]):
    def __init__(self, over: Enumeration[A], s: slice):
        super().__init__()
        self.over: Enumeration[A] = over
        self.s: slice = s

    class SizeComputation(ComputationStep):
        def __init__(self, outer: "EnumerationSlice[A]"):
            self.outer: "EnumerationSlice[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            s = self.outer.s
            start: int = s.start if s.start else 0
            step: int = s.step if s.step else 1
            stop: int = s.stop
            self.outer.size = (stop - start) // step
            yield EmptyStep()

    def size_computation(self) -> ComputationStep:
        return self.SizeComputation(self)

    class SliceComputation(ComputationStep):
        def __init__(self, outer: "EnumerationSlice[A]", index: int):
            self.outer: "EnumerationSlice[A]" = outer
            self.index: int = index

        def __iter__(self) -> Iterator[ComputationStep]:
            index = self.index
            s = self.outer.s
            start: int = s.start if s.start else 0
            step: int = s.step if s.step else 1
            outer_pos: int = 0
            outer_index: int = start + index * step

            while True:
                yield self.outer.over.cached_computation(outer_pos)
                outer_finite: Finite[A] = self.outer.over.get_values(outer_pos)
                yield outer_finite.cached_size_computation()
                outer_finite_size: int = outer_finite.size
                if outer_index < outer_finite_size:
                    yield outer_finite.cached_computation(outer_index)
                    self.outer.cache[index] = outer_finite.get_checked(outer_index)
                    break
                else:
                    outer_index -= outer_finite_size
                    outer_pos += 1
            yield EmptyStep()

    def computation(self, index: int) -> ComputationStep:
        return self.SliceComputation(self, index)

    class LocalClearCacheComputation(ComputationStep):
        def __init__(self, outer: "EnumerationSlice[A]"):
            self.outer: "EnumerationSlice[A]" = outer

        def __iter__(self) -> Iterator[ComputationStep]:
            yield self.outer.over.clear_cache_computation()
            yield Finite[A].clear_cache_computation(self.outer)

    def clear_cache_computation(self) -> ComputationStep:
        return self.LocalClearCacheComputation(self)


import fractions


class SchweinfurtNumbers:
    def __init__(self):
        self._fast = Enumeration.ints().map(self._rec)

    def _rec(self, n):
        if n < 0:
            return fractions.Fraction(0, 1)
        elif n == 0:
            return fractions.Fraction(1, 6)
        else:
            return fractions.Fraction(1, 6) * (
                -5 * self[n - 1] + 2 * self[n - 2] + self[n - 3]
            )

    def __getitem__(self, n):
        return 0 if n < 0 else self._fast[n]


if __name__ == "__main__":
    ints: Enumeration[int] = Enumeration.ints()
    print(ints[999999])

    ps = ints * ints
    p = ps.all_values()
    for _ in range(0, 10):
        print(*[y for y in next(p)], sep=",")

    xs = ints + ints
    for x in xs[0:10]:
        print(x)

    schweinf = SchweinfurtNumbers()
    for n in range(0, 7):
        print(schweinf[n])

    print(schweinf[99])
