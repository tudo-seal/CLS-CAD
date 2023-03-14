from typing import Literal

from pydantic import BaseModel

from cls_cps.util.hrid import generate_id


class JointOriginInf(BaseModel, frozen=True):
    motion: Literal["Rigid", "Revolute"]
    count: int
    requires: list
    provides: list


class MetaInf(BaseModel, frozen=True):
    partName: str
    forgeDocumentId: str
    forgeFolderId: str
    forgeProjectId: str
    cost: float = 1.0
    availability: float = 1.0


class PartConfigInf(BaseModel, frozen=True):
    requiresJointOrigins: list[str]
    providesJointOrigin: str


class PartInf(BaseModel, frozen=True):
    configurations: list[PartConfigInf]
    meta: MetaInf
    jointOrigins: dict[str, JointOriginInf]


class TaxonomyInf(BaseModel, frozen=True):
    forgeProjectId: str
    taxonomy: dict


class SynthesisRequestInf(BaseModel, frozen=True):
    forgeProjectId: str
    target: list[str]
    name: str | None = generate_id()
    tag: str | None = None
    source: list | None = None
    sourceUuid: str | None = None
    passedThroughTypes: list = []
