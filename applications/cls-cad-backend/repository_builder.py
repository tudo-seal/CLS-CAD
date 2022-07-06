from cls_python import *


class Jsonify:
    def __call__(self, x):
        return Jsonify(self.config, [*self.data, x], self.description)

    def __str__(self):
        return deep_str(self.data)

    def __init__(self, config, data, description):
        self.config = config
        self.data = data
        self.description = description

    def to_dict(self):
        return dict(
            part=self.description,
            provides=self.config.provides,
            forgeDocumentId=self.config.forgeDocumentID,
            forgeFolderId=self.config.forgeFolderId,
            forgeProjectId=self.config.forgeProjectID,
            **{
                label: part.to_dict()
                for (label, part) in zip(self.config.jointOrder, self.data)
            }
        )


class Part(object):
    def __call__(self, x):
        return Jsonify(x, [], self.payload)

    def __repr__(self):
        return ""

    def __str__(self):
        return ""

    def __eq__(self, other):
        return isinstance(other, Part)

    def __hash__(self):
        return hash(self.payload)

    def __init__(self, payload):
        # Create combinator type here based on some JSON payload in future
        self.payload = payload


# additional info about the parts configuration options
class PartConfig:
    def __init__(
        self, jointOrder, provides, forgeProjectId, forgeFolderId, forgeDocumentId
    ):
        # Create combinator type here based on some JSON payload in future
        self.forgeDocumentId = forgeDocumentId
        self.forgeFolderId = forgeFolderId
        self.forgeProjectId = forgeProjectId
        self.jointOrder = jointOrder
        self.provides = provides
