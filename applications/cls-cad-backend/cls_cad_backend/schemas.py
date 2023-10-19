from typing import Literal

from cls_cad_backend.util.hrid import generate_id
from pydantic import BaseModel, Field


class JointOriginInf(BaseModel, frozen=True):
    motion: Literal["Rigid", "Revolute"]
    count: int
    requires: list
    provides: list


class MetaInf(BaseModel, frozen=True):
    name: str
    forgeDocumentId: str
    forgeFolderId: str
    forgeProjectId: str
    cost: float = 1.0
    availability: float = 1.0


class PartConfigInf(BaseModel, frozen=True):
    requiresJointOrigins: list[str]
    providesJointOrigin: str


class CountNumOfPartTypeInf(BaseModel, frozen=True):
    partNumber: int
    partType: str


class PartInf(BaseModel, frozen=True):
    id: str = Field(..., alias="_id")
    configurations: list[PartConfigInf]
    meta: MetaInf
    jointOrigins: dict[str, JointOriginInf]


class TaxonomyInf(BaseModel, frozen=True):
    id: str = Field(..., alias="_id")
    forgeProjectId: str
    taxonomies: dict
    mappings: dict


class SynthesisRequestInf(BaseModel, frozen=True):
    forgeProjectId: str
    target: list[str]
    name: str | None = generate_id()
    tag: str | None = None
    partCounts: list[CountNumOfPartTypeInf] | None = None
    blacklist: list | None = None
    whitelist: list | None = None
    sourceUuid: str | None = None
    depths: list[int] | None = None
    resultsPerDepth: int = 10
