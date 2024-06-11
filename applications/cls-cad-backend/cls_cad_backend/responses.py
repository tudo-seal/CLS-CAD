import json
import typing

from starlette.responses import Response

base_json = True
try:  # pragma: no cover
    import orjson
    import ujson

    base_json = False
except ImportError:  # pragma: no cover
    pass


class FastResponse(Response):
    media_type = "application/json"

    def render(self, content: typing.Any) -> bytes:
        """
        Encodes the response of an endpoint into a JSON. When not running on PyPy, uses
        faster JSON encoders in a cascading fashion based on maximum JSON depth.

        :param content: The content to encode.
        :return: The encoded content.
        """
        if base_json:  # pragma: no cover
            return json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8")
        try:  # pragma: no cover
            return orjson.dumps(content, option=orjson.OPT_INDENT_2)
        except TypeError:  # pragma: no cover
            try:
                return ujson.dumps(content, indent=2, ensure_ascii=False).encode(
                    "utf-8"
                )
            except OverflowError:
                return json.dumps(content, indent=2, ensure_ascii=False).encode("utf-8")
