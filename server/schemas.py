"""Pydantic request/response models for the synchronisation API."""
from __future__ import annotations

from pydantic import BaseModel


# --- Auth -----------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str | None = None
    token: str


# --- Inspection upload ----------------------------------------------------
class ResponseItem(BaseModel):
    question_text: str
    answer: str | None = None
    comment: str | None = None
    is_no_go: bool = False


class InspectionUpload(BaseModel):
    uuid: str
    template_name: str
    result_mode: str = "standard"
    inspector_username: str | None = None
    inspector_name: str | None = None
    site_name: str | None = None
    asset_number: str | None = None
    registration: str | None = None
    department: str | None = None
    contractor: str | None = None
    general_comment: str | None = None
    start_time: str | None = None
    completion_time: str | None = None
    result: str | None = None
    responses: list[ResponseItem] = []


class UploadResult(BaseModel):
    status: str          # "created" or "duplicate"
    uuid: str
    id: int
    findings_created: int = 0
