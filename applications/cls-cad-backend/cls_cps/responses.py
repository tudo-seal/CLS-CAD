import json
import typing

from starlette.responses import Response

base_json = True
try:
    import orjson
    import ujson

    base_json = False
except ImportError:
    pass


class FastResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        if base_json:
            return json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8")
        try:
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
