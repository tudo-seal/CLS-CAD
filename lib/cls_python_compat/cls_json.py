import json

from .types import Arrow, Constructor, Intersection, Omega, Product


class CLSEncoder(json.JSONEncoder):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def combinator_hook(self, o):
        return json.JSONEncoder.default(self, o)

    def constructor_hook(self, o):
        return json.JSONEncoder.default(self, o)

    @staticmethod
    def tpe(o):
        # return f"{o.__class__.__module__}.{o.__class__.__qualname__}"
        return f"{o.__class__.__qualname__}"

    def default(self, o):
        if isinstance(o, Arrow):
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
                "name": o.name,
                "arg": self.default(o.arg),
            }
        elif isinstance(o, str):
            return {
                "__type__": CLSEncoder.tpe(Constructor("")),
                "name": o,
                "arg": Omega(),
            }
        else:
            return json.JSONEncoder.default(self, o)
