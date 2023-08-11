import json
import typing

import ujson
from starlette.responses import Response

no_orjson = False
try:
    from orjson import orjson
except ImportError:
    no_orjson = True


class FastResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        try:
            if no_orjson:
                raise TypeError
            return orjson.dumps(content, option=orjson.OPT_INDENT_2)
        except TypeError:
            try:
                return ujson.dumps(content, indent=2, ensure_ascii=False).encode(
                    "utf-8"
                )
            except OverflowError:
                return json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8")


class BytesResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        return content
