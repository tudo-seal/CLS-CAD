from .types import *
from .subtypes import Subtypes
from .fcl import InhabitationResult, FiniteCombinatoryLogic, Combinator, Apply, Failed, Rule, Tree
from .cls_json import CLSDecoder, CLSEncoder
from .debug_util import deep_str


# def deep_str(obj) -> str:
#     if isinstance(obj, list):
#         return f"[{','.join(map(deep_str, obj))}]"
#     elif isinstance(obj, dict):
#         return f"map([{','.join(map(lambda kv: ':'.join([deep_str(kv[0]), deep_str(kv[1])]) , obj.items()))}])"
#     elif isinstance(obj, set):
#         return f"set([{','.join(map(deep_str, obj))}])"
#     elif isinstance(obj, tuple):
#         return f"({','.join(map(deep_str, obj))})"
#     elif isinstance(obj, str):
#         return obj
#     elif isinstance(obj, Iterable):
#         return f"iter([{','.join(map(deep_str, obj))}])"
#     else:
#         return str(obj)
