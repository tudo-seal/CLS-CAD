import json

import jsonpickle

from .fcl import (
    Apply,
    Combinator,
    Failed,
    FiniteCombinatoryLogic,
    InhabitationResult,
    Tree,
)
from .subtypes import Subtypes
from .types import Arrow, Constructor, Intersection, Omega, Product


class CLSEncoder(json.JSONEncoder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def combinator_hook(self, o):
        return jsonpickle.encode(o)

    def constructor_hook(self, o):
        return o

    @staticmethod
    def tpe(o):
        # return f"{o.__class__.__module__}.{o.__class__.__qualname__}"
        return f"{o.__class__.__qualname__}"

    def default(self, o):
        if isinstance(o, Tree):
            return {
                "__type__": CLSEncoder.tpe(o),
                "rule": self.default(o.rule),
                "children": [self.default(c) for c in o.children],
            }
        elif isinstance(o, Combinator):
            return {
                "__type__": CLSEncoder.tpe(o),
                "target": self.default(o.target),
                "combinator": self.combinator_hook(o.combinator),
            }
        elif isinstance(o, Apply):
            return {
                "__type__": CLSEncoder.tpe(o),
                "target": self.default(o.target),
                "function_type": self.default(o.function_type),
                "argument_type": self.default(o.argument_type),
            }
        elif isinstance(o, Failed):
            return {"__type__": CLSEncoder.tpe(o), "target": self.default(o.target)}
        elif isinstance(o, Arrow):
            return {
                "__type__": CLSEncoder.tpe(o),
                "source": self.default(o.source),
                "target": self.default(o.target),
            }
        elif isinstance(o, Intersection):
            return {
                "__type__": CLSEncoder.tpe(o),
                "left": self.default(o.left),
                "right": self.default(o.right),
            }
        elif isinstance(o, Product):
            return {
                "__type__": CLSEncoder.tpe(o),
                "left": self.default(o.left),
                "right": self.default(o.right),
            }
        elif isinstance(o, Omega):
            return {"__type__": CLSEncoder.tpe(o)}
        elif isinstance(o, Constructor):
            return {
                "__type__": CLSEncoder.tpe(o),
                "name": self.constructor_hook(o.name),
                "arg": self.default(o.arg),
            }
        elif isinstance(o, Subtypes):
            return {
                "__type__": CLSEncoder.tpe(o),
                "environment": {
                    self.constructor_hook(k): [self.constructor_hook(c) for c in v]
                    for k, v in o.environment.items()
                },
            }
        elif isinstance(o, InhabitationResult):
            return {
                "__type__": CLSEncoder.tpe(o),
                "targets": [self.default(t) for t in o.targets],
                "rules": [self.default(r) for r in o.rules],
            }
        elif isinstance(o, FiniteCombinatoryLogic):
            return {
                "__type__": CLSEncoder.tpe(o),
                "repository": {
                    self.combinator_hook(c): self.default(t) for c, t in o.repository
                },
                "subtypes": self.default(o.subtypes),
                "processes": self.default(o.processes),
            }
        else:
            return json.JSONEncoder.default(self, o)


class CLSDecoder(json.JSONDecoder):
    def __init__(self, **kwargs):
        super().__init__(object_hook=self, **kwargs)

    def combinator_hook(self, dct):
        return jsonpickle.decode(dct)

    def constructor_hook(self, dct):
        return dct

    @staticmethod
    def tpe(cls):
        # return f"{cls.__module__}.{cls.__qualname__}"
        return f"{cls.__qualname__}"

    def __call__(self, dct):
        if "__type__" in dct:
            tpe = dct["__type__"]
            if tpe == CLSDecoder.tpe(Tree):
                return Tree(rule=dct["rule"], children=tuple(dct["children"]))
            elif tpe == CLSDecoder.tpe(Combinator):
                return Combinator(
                    target=dct["target"],
                    combinator=self.combinator_hook(dct["combinator"]),
                )
            elif tpe == CLSDecoder.tpe(Apply):
                return Apply(
                    target=dct["target"],
                    function_type=dct["function_type"],
                    argument_type=dct["argument_type"],
                )
            elif tpe == CLSDecoder.tpe(Failed):
                return Failed(target=dct["target"])
            elif tpe == CLSDecoder.tpe(Arrow):
                return Arrow(source=dct["source"], target=dct["target"])
            elif tpe == CLSDecoder.tpe(Intersection):
                return Intersection(left=dct["left"], right=dct["right"])
            elif tpe == CLSDecoder.tpe(Product):
                return Product(left=dct["left"], right=dct["right"])
            elif tpe == CLSDecoder.tpe(Omega):
                return Omega()
            elif tpe == CLSDecoder.tpe(Constructor):
                return Constructor(
                    name=self.constructor_hook(dct["name"]), arg=dct["arg"]
                )
            elif tpe == CLSDecoder.tpe(Subtypes):
                return Subtypes(
                    environment={
                        self.constructor_hook(k): {
                            self.constructor_hook(st) for st in v
                        }
                        for k, v in dct["environment"].items()
                    }
                )
            elif tpe == CLSDecoder.tpe(InhabitationResult):
                return InhabitationResult(
                    targets=dct["targets"], rules={r for r in dct["rules"]}
                )
            elif tpe == CLSDecoder.tpe(FiniteCombinatoryLogic):
                return FiniteCombinatoryLogic(
                    repository={
                        self.combinator_hook(k): v for k, v in dct["repository"].items()
                    },
                    subtypes=dct["subtypes"],
                    processes=dct["processes"],
                )
            else:
                return dct
        return dct
