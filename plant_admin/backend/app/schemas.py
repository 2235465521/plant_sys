from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["admin", "user"]
    username: str


class RegisterStatus(BaseModel):
    enabled: bool
    allow_admin: bool


class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    password_confirm: str = Field(min_length=1, max_length=128)
    role: Literal["admin", "user"] = "user"

    @field_validator("username")
    @classmethod
    def username_strip(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def check_passwords(self) -> RegisterRequest:
        if self.password != self.password_confirm:
            raise ValueError("两次输入的密码不一致")
        if len(self.username) < 2:
            raise ValueError("用户名至少 2 个字符")
        return self


class UserBrief(BaseModel):
    id: int
    username: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class UserRoleUpdate(BaseModel):
    role: Literal["admin", "user"]


class PlantBase(BaseModel):
    division: Optional[str] = None
    subclass: Optional[str] = None
    taxonomic_order: Optional[str] = None
    family: Optional[str] = None
    genus: Optional[str] = None
    vernacular_name: Optional[str] = None
    alternative_names_zh: Optional[str] = None
    scientific_name: Optional[str] = None
    taxonomic_provenance: Optional[str] = None
    synonyms: Optional[str] = None
    morphology_text: Optional[str] = None
    medicinal_shape: Optional[str] = None
    distribution_china: Optional[str] = None
    distribution_abroad: Optional[str] = None
    habitat: Optional[str] = None
    is_medicinal_food_homologous: Optional[str] = None
    image_url: Optional[str] = None
    image_server_paths: Optional[list[str]] = None

    @field_validator("image_server_paths", mode="before")
    @classmethod
    def coerce_image_server_paths(cls, v: Any) -> Optional[list[str]]:
        if v is None:
            return None
        if isinstance(v, bytes):
            v = v.decode("utf-8", errors="replace")
        if isinstance(v, str):
            t = v.strip()
            if not t:
                return None
            if t.startswith("["):
                try:
                    parsed = json.loads(t)
                except json.JSONDecodeError:
                    return None
                if not isinstance(parsed, list):
                    return None
                out = [str(x).strip() for x in parsed if x is not None and str(x).strip()]
                return out or None
            return [t]
        if isinstance(v, list):
            out = [str(x).strip() for x in v if x is not None and str(x).strip()]
            return out or None
        return None


class PlantCreate(PlantBase):
    pass


class PlantUpdate(PlantBase):
    pass


class PlantOut(PlantBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class PlantListOut(BaseModel):
    items: list[PlantOut]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)


class PlantExportBatchIn(BaseModel):
    ids: list[int] = Field(..., min_length=1, description="要导出的物种 id，将去重")
    file_format: Literal["txt", "xlsx"] = Field(default="txt", description="导出格式")


class PlantImageDownloadLogIn(BaseModel):
    """前端下载本站托管图片（转 JPG）后写入导出审计日志。"""
    mode: Literal["current", "batch"]
    image_count: int = Field(default=1, ge=1)


class PlantDeleteServerImageIn(BaseModel):
    """删除本站托管的一张图：站内路径必须属于 /api/media/plants/{物种id}/ 下的文件。"""
    path: str = Field(..., min_length=1)

    @field_validator("path")
    @classmethod
    def normalize_path(cls, v: Any) -> str:
        if v is None:
            raise ValueError("path 不能为空")
        s = str(v).strip().split("?", 1)[0].strip()
        if not s:
            raise ValueError("path 不能为空")
        return s


class TaxonBucket(BaseModel):
    value: str
    count: int


class TaxonomyDistinctOut(BaseModel):
    field: str
    items: list[TaxonBucket]


class ExportLogOut(BaseModel):
    id: int
    plant_id: Optional[int]
    plant_name: Optional[str]
    user_id: int
    username: str
    user_role: Optional[Literal["admin", "user"]] = None
    export_format: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExportLogListOut(BaseModel):
    items: list[ExportLogOut]
    total: int
    page: int
    page_size: int
