import functools
import itertools
from collections import deque
from typing import TypeAlias, Callable, Tuple, Iterable, Any
from multiprocessing import Pool
import os
from collections.abc import Iterator

from abc import ABC, abstractmethod
from itertools import chain
from functools import partial, cached_property

from .enumeration import Enumeration, ComputationStep, EmptyStep
from .types import *
from .subtypes import Subtypes


MultiArrow: TypeAlias = Tuple[list[Type], Type]
State: TypeAlias = list['MultiArrow']
CoverMachineInstruction: TypeAlias = Callable[[State], Tuple[State, list['CoverMachineInstruction']]]


@dataclass(frozen=True)
class Rule(ABC):
    target: Type = field(init=True, kw_only=True)
    is_combinator: bool = field(init=True, kw_only=True)


@dataclass(frozen=True)
class Failed(Rule):
    target: Type = field()
    is_combinator: bool = field(default=False, init=False)

    def __str__(self):
        return f"Failed({str(self.target)})"


@dataclass(frozen=True)
class Combinator(Rule):
    target: Type = field()
    is_combinator: bool = field(default=True, init=False)
    combinator: object = field(init=True)

    def __str__(self):
        return f"Combinator({str(self.target)}, {str(self.combinator)})"


@dataclass(frozen=True)
class Apply(Rule):
    target: Type = field()
    is_combinator: bool = field(default=False, init=False)
    function_type: Type = field(init=True)
    argument_type: Type = field(init=True)

    def __str__(self):
        return f"@({str(self.function_type)}, {str(self.argument_type)}) : {self.target}"


@dataclass(frozen=True)
class Tree(object):
    rule: Rule = field(init=True)
    children: Tuple['Tree', ...] = field(init=True, default_factory=lambda: ())

    class Evaluator(ComputationStep):
        def __init__(self, outer: 'Tree', results: list[Any]):
            self.outer: 'Tree' = outer
            self.results = results

        def __iter__(self) -> Iterator[ComputationStep]:
            match self.outer.rule:
                case Combinator(_, c):
                    self.results.append(c)
                case Apply(_, _, _):
                    f_arg = list()
                    yield Tree.Evaluator(self.outer.children[0], f_arg)
                    yield Tree.Evaluator(self.outer.children[1], f_arg)
                    self.results.append(partial(f_arg[0])(f_arg[1]))
                case _:
                    raise TypeError(f"Cannot apply rule: {self.outer.rule}")
            yield EmptyStep()

    def evaluate(self) -> Any:
        result: list[Any] = []
        self.Evaluator(self, result).run()
        return result[0]

    def __str__(self):
        match self.rule:
            case Combinator(_, _): return str(self.rule)
            case Apply(_, _, _): return f"{str(self.children[0])}({str(self.children[1])})"
            case _: return f"{str(self.rule)} @ ({', '.join(map(str, self.children))})"


@dataclass(frozen=True)
class InhabitationResult(object):
    targets: list[Type] = field(init=True)
    rules: set[Rule] = field(init=True)

    @cached_property
    def grouped_rules(self) -> dict[Type, set[Rule]]:
        result: dict[Type, set[Rule]] = dict()
        for rule in self.rules:
            group: set[Rule] = result.get(rule.target)
            if group:
                group.add(rule)
            else:
                result[rule.target] = {rule}
        return result

    def check_empty(self, target: Type) -> bool:
        for rule in self.grouped_rules.get(target, {Failed(target)}):
            if isinstance(rule, Failed):
                return True
        return False

    @cached_property
    def non_empty(self) -> bool:
        for target in self.targets:
            if self.check_empty(target):
                return False
        return bool(self.targets)

    def __bool__(self) -> bool:
        return self.non_empty

    @cached_property
    def infinite(self) -> bool:
        if not self:
            return False

        reachable: dict[Type, set[Type]] = dict()
        for (target, rules) in self.grouped_rules.items():
            entry: set[Type] = set()
            for rule in rules:
                match rule:
                    case Apply(target, lhs, rhs):
                        next_reached: set[Type] = {lhs, rhs}
                        entry.update(next_reached)
                    case _:
                        pass
            reachable[target] = entry

        changed: bool = True
        to_check: set[Type] = set(self.targets)
        while changed:
            changed = False
            next_to_check = set()
            for target in to_check:
                can_reach = reachable[target]
                if target in can_reach:
                    return True
                newly_reached = set().union(*(reachable[reached] for reached in can_reach))
                for new_target in newly_reached:
                    if target == new_target:
                        return True
                    elif new_target not in to_check:
                        changed = True
                        next_to_check.add(new_target)
                        can_reach.add(new_target)
                    elif new_target not in can_reach:
                        changed = True
                        can_reach.add(new_target)
            to_check.update(next_to_check)
        return False

    def size(self) -> int:
        if self.infinite:
            return -1
        maximum = self.raw.unsafe_max_size()
        size = 0
        values = self.raw.all_values()
        for i in range(0, maximum+1):
            trees = next(values)
            size += len(trees)
        return size

    def __getitem__(self, target: Type) -> Enumeration[Tree]:
        if target in self.enumeration_map:
            return self.enumeration_map[target]
        else:
            return Enumeration.empty()

    @staticmethod
    def combinator_result(r: Combinator) -> Enumeration[Tree]:
        return Enumeration.singleton(Tree(r, ()))

    @staticmethod
    def apply_result(result: dict[Type, Enumeration[Tree]], r: Apply) -> Enumeration[Tree]:
        def mkapp(left_and_right):
            return Tree(r, (left_and_right[0], left_and_right[1]))

        def apf():
            return (result[r.function_type] * result[r.argument_type]) \
                    .map(mkapp).pay()
        applied = Enumeration.lazy(apf)
        return applied

    @cached_property
    def enumeration_map(self) -> dict[Type, Enumeration[Tree]]:
        result: dict[Type, Enumeration[Tree]] = dict()
        for (target, rules) in self.grouped_rules.items():
            _enum: Enumeration[Tree] = Enumeration.empty()
            for rule in rules:
                match rule:
                    case Combinator(_, _) as r:
                        _enum = _enum + InhabitationResult.combinator_result(r)
                    case Apply(_, _, _) as r:
                        _enum = _enum + InhabitationResult.apply_result(result, r)
                    case _:
                        pass
            result[target] = _enum
        return result

    @cached_property
    def raw(self) -> Enumeration[Tree | list[Tree]]:
        if not self:
            return Enumeration.empty()
        if len(self.targets) == 1:
            return self.enumeration_map[self.targets[0]]
        else:
            result: Enumeration[list[Tree]] = Enumeration.singleton([])
            for target in self.targets:
                result = (result * self.enumeration_map[target]).map(lambda x: [*x[0], x[1]])
            return result

    @cached_property
    def evaluated(self) -> Enumeration[Any | list[Any]]:
        if len(self.targets) == 1:
            return self.raw.map(lambda t: t.evaluate())
        else:
            return self.raw.map(lambda l: list(map(lambda t: t.evaluate(), l)))


class FiniteCombinatoryLogic(object):

    def __init__(self, repository: dict[object, Type], subtypes: Subtypes, processes=os.cpu_count()):
        self.processes = processes

        self.repository = repository
        with Pool(processes) as pool:
            self.splitted_repository: dict[object, list[list[MultiArrow]]] = \
                dict(pool.starmap(FiniteCombinatoryLogic._split_repo,
                     self.repository.items(),
                     chunksize=max(len(self.repository) // processes, 10)))
        self.subtypes = subtypes

    @staticmethod
    def _split_repo(c: object, ty: Type) -> Tuple[object, list[list[MultiArrow]]]:
        return c, FiniteCombinatoryLogic.split_ty(ty)

    @staticmethod
    def split_ty(ty: Type) -> list[list[MultiArrow]]:
        def safe_split(xss: list[list[MultiArrow]]) -> Tuple[list[MultiArrow], list[list[MultiArrow]]]:
            return (xss[0] if xss else []), xss[1:]

        def split_rec(to_split: Type, srcs: list[Type], delta: list[list[MultiArrow]]) -> list[list[MultiArrow]]:
            match to_split:
                case Arrow(src, tgt):
                    xs, xss = safe_split(delta)
                    next_srcs = [src, *srcs]
                    return [[(next_srcs, tgt), *xs], *split_rec(tgt, next_srcs, xss)]
                case Intersection(sigma, tau) if sigma.is_omega:
                    return split_rec(tau, srcs, delta)
                case Intersection(sigma, tau) if tau.is_omega:
                    return split_rec(sigma, srcs, delta)
                case Intersection(sigma, tau):
                    return split_rec(sigma, srcs, split_rec(tau, srcs, delta))
                case _:
                    return delta

        return [] if ty.is_omega else [[([], ty)], *split_rec(ty, [], [])]

    def _dcap(self, sigma: Type, tau: Type) -> Type:
        if self.subtypes.check_subtype(sigma, tau):
            return sigma
        elif self.subtypes.check_subtype(tau, sigma):
            return tau
        else:
            return Intersection(sigma, tau)

    @staticmethod
    def _partition_cover(covered: set[Type], to_cover: set[Type]) -> Tuple[set[Type], set[Type]]:
        in_covered: set[Type] = set()
        not_in_covered: set[Type] = set()
        for ty in to_cover:
            if ty in covered:
                in_covered.add(ty)
            else:
                not_in_covered.add(ty)
        return in_covered, not_in_covered

    @staticmethod
    def _still_possible(splits: list[Tuple[MultiArrow, set[Type]]], to_cover: set[Type]) -> bool:
        for ty in to_cover:
            if not any(ty in covered for _, covered in splits):
                return False
        return True

    def _merge_multi_arrow(self, arrow1: MultiArrow, arrow2: MultiArrow) -> MultiArrow:
        return list(map(self._dcap, arrow1[0], arrow2[0])), self._dcap(arrow1[1], arrow2[1])

    def _check_cover(self, splits: list[Tuple[MultiArrow, set[Type]]], to_cover: set[Type]) -> CoverMachineInstruction:
        def instr(state: list[MultiArrow]) -> Tuple[State, list[CoverMachineInstruction]]:
            if FiniteCombinatoryLogic._still_possible(splits, to_cover):
                return state, [self._cover(splits, to_cover)]
            else:
                return state, []

        return instr

    def _check_continue_cover(self, splits: list[Tuple[MultiArrow, set[Type]]],
                              to_cover: set[Type],
                              current_result: MultiArrow) -> CoverMachineInstruction:
        def instr(state: list[MultiArrow]) -> Tuple[State, list[CoverMachineInstruction]]:
            if FiniteCombinatoryLogic._still_possible(splits, to_cover):
                return state, [self._continue_cover(splits, to_cover, current_result)]
            else:
                return state, []

        return instr

    def _continue_cover(self, splits: list[Tuple[MultiArrow, set[Type]]],
                        to_cover: set[Type],
                        current_result: MultiArrow) -> CoverMachineInstruction:
        def instr(state: list[MultiArrow]) -> Tuple[State, list[CoverMachineInstruction]]:
            if not splits:
                return state, []
            m, covered = splits[0]
            _splits = splits[1:]
            freshly_covered, uncovered = FiniteCombinatoryLogic._partition_cover(covered, to_cover)
            if not freshly_covered:
                return state, [self._continue_cover(_splits, to_cover, current_result)]
            merged = self._merge_multi_arrow(current_result, m)
            if not uncovered:
                return [merged, *state], [self._continue_cover(_splits, to_cover, current_result)]
            elif merged[0] == current_result[0]:
                return state, [self._continue_cover(_splits, uncovered, merged)]
            else:
                return state, [self._continue_cover(_splits, uncovered, merged),
                               self._check_continue_cover(_splits, to_cover, current_result)]

        return instr

    def _cover(self, splits: list[Tuple[MultiArrow, set[Type]]], to_cover: set[Type]) -> CoverMachineInstruction:
        def instr(state: list[MultiArrow]) -> Tuple[State, list[CoverMachineInstruction]]:
            if not splits:
                return state, []
            m, covered = splits[0]
            _splits = splits[1:]
            freshly_covered, uncovered = FiniteCombinatoryLogic._partition_cover(covered, to_cover)
            if not freshly_covered:
                return state, [self._cover(_splits, to_cover)]
            elif not uncovered:
                return [m, *state], [self._check_cover(_splits, to_cover)]
            else:
                return state, [self._continue_cover(_splits, uncovered, m),
                               self._check_cover(_splits, to_cover)]

        return instr

    @staticmethod
    def _cover_machine(state: State, program: list[CoverMachineInstruction]) -> State:
        instructions: deque[Iterator[CoverMachineInstruction]] = deque([iter(program)])
        while instructions:
            head = instructions.popleft()
            try:
                instruction = next(head)
                instructions.appendleft(head)
                state, next_instructions = instruction(state)
                instructions.appendleft(iter(next_instructions))
            except StopIteration:
                pass
        return state

    def _reduce_multi_arrows(self, ms: list[MultiArrow]) -> list[MultiArrow]:
        def check(lesser_arg_vect: MultiArrow, greater_arg_vect: MultiArrow) -> bool:
            (lesser_args, greater_args) = (lesser_arg_vect[0], greater_arg_vect[0])
            return (len(lesser_args) == len(greater_args)
                    and all(self.subtypes.check_subtype(lesser_arg, greater_arg)
                            for (lesser_arg, greater_arg) in zip(lesser_args, greater_args)))

        def average_arguments_type_size(m: MultiArrow) -> int:
            size: int = 0
            for ty in m[0]:
                size += ty.size
            return size / len(m[0]) if m[0] else 0

        result: list[MultiArrow] = []
        for multi_arrow in sorted(ms, key=average_arguments_type_size):
            if all(not check(multi_arrow, in_result) for in_result in result):
                result = [multi_arrow, *(in_result for in_result in result if not check(in_result, multi_arrow))]
        return result

    def _compute_fail_existing(self, rules: set[Rule], target: Type) -> Tuple[bool, bool]:
        rest_of_rules: Iterator[Rule] = iter(rules)
        while to_check := next(rest_of_rules, None):
            match to_check:
                case Failed(t) if t == target:
                    return True, True
                case Failed(t) if self.subtypes.check_subtype(target, t):
                    return True, Failed(target) in rest_of_rules
                case Apply(_, _, arg) if arg == target:
                    return False, True
                case _:
                    continue
        return False, False

    @staticmethod
    def _commit_multi_arrow(combinator: object, m: MultiArrow) -> deque[Rule]:
        result: deque[Rule] = deque()
        srcs, tgt = m
        for src in srcs:
            arr = Arrow(src, tgt)
            result.appendleft(Apply(tgt, arr, src))
            tgt = arr
        result.appendleft(Combinator(tgt, combinator))
        return result

    @staticmethod
    def _commit_updates(target: Type,
                        combinator: object,
                        covers: Sequence[MultiArrow]) -> deque[deque[Rule]]:
        result: deque[deque[Rule]] = deque()
        for cover in covers:
            result.append(FiniteCombinatoryLogic._commit_multi_arrow(combinator, (cover[0], target)))
        return result

    def _accumulate_covers(self,
                           target: Type,
                           to_cover: set[Type],
                           combinator: object,
                           combinator_type: list[list[MultiArrow]]) -> Tuple[deque[deque[Rule]], bool]:
        def cover_instr(ms: list[MultiArrow]) -> CoverMachineInstruction:
            splits: list[(MultiArrow, set[Type])] = \
                list(map(lambda m: (m, set(filter(lambda b: self.subtypes.check_subtype(m[1], b), to_cover))), ms))
            return self._cover(splits, to_cover)

        covers: list[MultiArrow] = self._cover_machine([], list(map(cover_instr, combinator_type)))
        next_rules: deque[deque[Rule]] = \
            FiniteCombinatoryLogic._commit_updates(target, combinator, self._reduce_multi_arrows(covers))
        return next_rules, not covers

    def _inhabit_cover(self, target: Type, todo_rules: deque[deque[Rule]]) -> bool:
        prime_factors: set[Type] = self.subtypes.minimize(target.organized)
        with Pool(self.processes) as pool:
            results =\
                pool.starmap(
                    partial(self._accumulate_covers, target, prime_factors),
                    self.splitted_repository.items(),
                    max(len(self.splitted_repository) // self.processes, 10))
        failed: bool = True
        for rules, local_fail in results:
            if not local_fail:
                failed = False
                todo_rules.extend(rules)
        return failed

    def _omega_rules(self, target: Type) -> set[Rule]:
        return {Apply(target, target, target),
                *map(lambda c: Combinator(target, c), self.splitted_repository.keys())}

    def _inhabitation_step(self, stable: set[Rule], targets: deque[deque[Rule]]) -> bool:
        if targets:
            if targets[0]:
                target = targets[0].popleft()
                match target:
                    case Combinator(_, _):
                        stable.add(target)
                    case Apply(_, _, _) if target in stable:
                        pass
                    case Apply(_, _, target_type):
                        failed, existing = self._compute_fail_existing(stable, target_type)
                        if failed:
                            if not existing:
                                stable.add(Failed(target_type))
                        elif existing:
                            stable.add(target)
                        elif target_type.is_omega:
                            stable |= self._omega_rules(target_type)
                            stable.add(target)
                        else:
                            inhabit_failed = self._inhabit_cover(target_type, targets)
                            if inhabit_failed:
                                stable.add(Failed(target_type))
                                targets.popleft()
                            else:
                                stable.add(target)
                    case _:
                        raise TypeError(f"Invalid type of rule: {target}")
            else:
                targets.popleft()
        return bool(targets)

    def _inhabitation_machine(self, stable: set[Rule], targets: deque[deque[Rule]]):
        while self._inhabitation_step(stable, targets):
            pass

    def inhabit(self, *targets: Type) -> InhabitationResult:
        result: set[Rule] = set()
        all_targets = list(targets)
        todo_rules: deque[deque[Rule]] = deque()
        for target in all_targets:
            if target.is_omega:
                result |= self._omega_rules(target)
            else:
                failed, existing = self._compute_fail_existing(result, target)
                if failed:
                    if not existing:
                        result.add(Failed(target))
                else:
                    inhabit_failed = self._inhabit_cover(target, todo_rules)
                    if inhabit_failed:
                        result.add(Failed(target))
                    else:
                        self._inhabitation_machine(result, todo_rules)
        return InhabitationResult(targets=all_targets, rules=FiniteCombinatoryLogic._prune(result))

    @staticmethod
    def _ground_types_of(rules: set[Rule]) -> set[Type]:
        ground: set[Type] = set()
        next_ground: set[Type] = set(rule.target for rule in rules if rule.is_combinator)

        while next_ground:
            ground |= next_ground
            next_ground = set()
            for rule in rules:
                match rule:
                    case Apply(target, function_type, argument_type) if (function_type in ground
                                                                         and argument_type in ground
                                                                         and target not in ground):
                        next_ground.add(target)
                    case _: pass
        return ground

    @staticmethod
    def _prune(rules: set[Rule]) -> set[Rule]:
        ground_types: set[Type] = FiniteCombinatoryLogic._ground_types_of(rules)
        result = set()
        for rule in rules:
            match rule:
                case Apply(target, _, _) if target not in ground_types:
                    result.add(Failed(target))
                case Apply(_, function_type, argument_type) if not (function_type in ground_types
                                                                    and argument_type in ground_types):
                    continue
                case _:
                    result.add(rule)
        return result

