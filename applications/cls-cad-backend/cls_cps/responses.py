import json
import typing

import ujson
from orjson import orjson
from starlette.responses import Response


class FastResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        try:
            return orjson.dumps(content, option=orjson.OPT_INDENT_2)
        except TypeError:
            try:
                print("Falling back to UJSON")
                return ujson.dumps(content, indent=2, ensure_ascii=False).encode(
                    "utf-8"
                )
            except OverflowError:
                print("Falling back to default JSON.")
                return json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8")
