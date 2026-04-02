from __future__ import annotations
import json as _json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4
from pydantic import BaseModel, field_validator, model_validator
from sqlalchemy import String, Text, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column
from ee.base import EEBase


class Blueprint(EEBase):
    __tablename__ = "blueprints"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    type: Mapped[str] = mapped_column(String)  # RUNTIME, NETWORK
    name: Mapped[str] = mapped_column(String, unique=True)
    definition: Mapped[str] = mapped_column(Text)  # JSON blob
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    os_family: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # DEBIAN, ALPINE — set on RUNTIME blueprints


class Artifact(EEBase):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    filename: Mapped[str] = mapped_column(String)
    content_type: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String)
    size_bytes: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ApprovedOS(EEBase):
    __tablename__ = "approved_os"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True)  # e.g. Debian 12
    image_uri: Mapped[str] = mapped_column(String)  # e.g. debian:12-slim
    os_family: Mapped[str] = mapped_column(String)  # DEBIAN, ALPINE, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)


class CapabilityMatrix(EEBase):
    __tablename__ = "capability_matrix"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_os_family: Mapped[str] = mapped_column(String)  # DEBIAN, ALPINE, etc.
    tool_id: Mapped[str] = mapped_column(String)  # e.g., python-3.11
    injection_recipe: Mapped[str] = mapped_column(Text)  # Dockerfile snippet
    validation_cmd: Mapped[str] = mapped_column(String)
    artifact_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # No ForeignKey("artifacts.id") — drop FK per plan to avoid cross-table dependency issues
    runtime_dependencies: Mapped[str] = mapped_column(Text, default="[]", server_default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class PuppetTemplate(EEBase):
    __tablename__ = "puppet_templates"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    friendly_name: Mapped[str] = mapped_column(String, unique=True)
    runtime_blueprint_id: Mapped[str] = mapped_column(String)  # FK to blueprints.id
    network_blueprint_id: Mapped[str] = mapped_column(String)  # FK to blueprints.id
    canonical_id: Mapped[str] = mapped_column(String)  # Hash of ingredients
    current_image_uri: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_built_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_compliant: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", server_default="'DRAFT'")
    bom_captured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class ImageBOM(EEBase):
    __tablename__ = "image_boms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(36))
    # No ForeignKey("puppet_templates.id") — drop FK per plan spec to avoid intra-EEBase dependency issues
    raw_data_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PackageIndex(EEBase):
    __tablename__ = "package_index"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    template_id: Mapped[str] = mapped_column(String(36))
    # No ForeignKey("puppet_templates.id") — drop FK per plan spec
    name: Mapped[str] = mapped_column(String(255), index=True)
    version: Mapped[str] = mapped_column(String(50), index=True)
    type: Mapped[str] = mapped_column(String(20))  # 'pip' or 'apt'


# ---------------------------------------------------------------------------
# Pydantic request / response models (EE-owned)
# ---------------------------------------------------------------------------

class ImageBuildRequest(BaseModel):
    tag: str
    capabilities: Dict[str, str]


class ImageResponse(BaseModel):
    tag: str
    image_uri: str
    status: str
    created_at: datetime


class BlueprintCreate(BaseModel):
    type: str  # RUNTIME, NETWORK
    name: str
    definition: Dict
    os_family: Optional[str] = None          # required for RUNTIME, ignored for NETWORK
    confirmed_deps: Optional[List[str]] = None  # dep-confirmation resubmit

    @field_validator('os_family', mode='before')
    @classmethod
    def normalize_os_family(cls, v):
        return v.upper() if isinstance(v, str) else v

    @model_validator(mode='after')
    def runtime_requires_os_family(self):
        if self.type == 'RUNTIME' and not self.os_family:
            raise ValueError("os_family is required for RUNTIME blueprints")
        return self


class BlueprintResponse(BaseModel):
    id: str
    type: str
    name: str
    definition: Dict
    version: int
    created_at: datetime
    os_family: Optional[str] = None  # nullable — network blueprints have no os_family

    class Config:
        from_attributes = True


class CapabilityMatrixEntry(BaseModel):
    id: Optional[int] = None
    base_os_family: str
    tool_id: str
    injection_recipe: str
    validation_cmd: str
    artifact_id: Optional[str] = None
    runtime_dependencies: List[str] = []
    is_active: bool = True

    @field_validator('runtime_dependencies', mode='before')
    @classmethod
    def deserialize_runtime_deps(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return _json.loads(v)
            except Exception:
                return []
        return v

    @field_validator('base_os_family', mode='before')
    @classmethod
    def normalize_os_family(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v

    class Config:
        from_attributes = True


class CapabilityMatrixUpdate(BaseModel):
    base_os_family: Optional[str] = None
    tool_id: Optional[str] = None
    injection_recipe: Optional[str] = None
    validation_cmd: Optional[str] = None
    artifact_id: Optional[str] = None
    runtime_dependencies: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator('base_os_family', mode='before')
    @classmethod
    def normalize_os(cls, v: Any) -> Any:
        return v.upper() if isinstance(v, str) else v


class ArtifactResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    sha256: str
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovedOSCreate(BaseModel):
    name: str
    image_uri: str
    os_family: str


class ApprovedOSUpdate(BaseModel):
    name: Optional[str] = None
    image_uri: Optional[str] = None
    os_family: Optional[str] = None


class ApprovedOSResponse(BaseModel):
    id: int
    name: str
    image_uri: str
    os_family: str

    class Config:
        from_attributes = True


class PuppetTemplateCreate(BaseModel):
    friendly_name: str
    runtime_blueprint_id: str
    network_blueprint_id: str


class PuppetTemplateResponse(BaseModel):
    id: str
    friendly_name: str
    runtime_blueprint_id: str
    network_blueprint_id: str
    canonical_id: str
    current_image_uri: Optional[str] = None
    last_built_image: Optional[str] = None
    last_built_at: Optional[datetime] = None
    created_at: datetime
    is_compliant: bool = True
    status: str = "DRAFT"
    bom_captured: bool = False

    class Config:
        from_attributes = True


class ImageBOMResponse(BaseModel):
    id: str
    template_id: str
    raw_data_json: str
    created_at: datetime

    class Config:
        from_attributes = True


class PackageIndexResponse(BaseModel):
    id: str
    template_id: str
    name: str
    version: str
    type: str  # 'pip', 'apt'

    class Config:
        from_attributes = True
