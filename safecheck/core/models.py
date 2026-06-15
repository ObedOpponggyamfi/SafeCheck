"""SQLAlchemy ORM models — the complete offline schema.

Every table named in the specification is defined here so the schema is
complete from day one, even though Phase One only actively populates a subset.
Checklist questions live in the database (not in hard-coded screens) so a single
Yes/No/N/A interface can render every checklist.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from safecheck.core.database import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp used for created/updated columns."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    """Generate a string UUID for offline-created records."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# People and organisation
# ---------------------------------------------------------------------------
class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(200), default=None)

    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"))
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(160), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    role: Mapped["Role"] = relationship(back_populates="users")


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str | None] = mapped_column(String(20))

    departments: Mapped[list["Department"]] = relationship(back_populates="site")


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"))

    site: Mapped["Site"] = relationship(back_populates="departments")


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(120))


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------
class AssetCategory(Base):
    __tablename__ = "asset_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)

    assets: Mapped[list["Asset"]] = relationship(back_populates="category")


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("asset_categories.id"))
    asset_number: Mapped[str] = mapped_column(String(60), index=True)
    registration_number: Mapped[str | None] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(String(160))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    contractor_id: Mapped[int | None] = mapped_column(ForeignKey("contractors.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["AssetCategory"] = relationship(back_populates="assets")
    department: Mapped["Department"] = relationship()
    contractor: Mapped["Contractor"] = relationship()


# ---------------------------------------------------------------------------
# Checklist templates (data-driven questions)
# ---------------------------------------------------------------------------
class ChecklistTemplate(Base):
    __tablename__ = "checklist_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("asset_categories.id"))
    result_mode: Mapped[str] = mapped_column(String(20), default="standard")
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    category: Mapped["AssetCategory"] = relationship()
    sections: Mapped[list["ChecklistSection"]] = relationship(
        back_populates="template", cascade="all, delete-orphan"
    )
    questions: Mapped[list["ChecklistQuestion"]] = relationship(
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="ChecklistQuestion.display_order",
    )


class ChecklistSection(Base):
    __tablename__ = "checklist_sections"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("checklist_templates.id"))
    title: Mapped[str] = mapped_column(String(120))
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    template: Mapped["ChecklistTemplate"] = relationship(back_populates="sections")


class ChecklistQuestion(Base):
    __tablename__ = "checklist_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("checklist_templates.id"))
    section_id: Mapped[int | None] = mapped_column(ForeignKey("checklist_sections.id"))
    text: Mapped[str] = mapped_column(String(255))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    is_no_go: Mapped[bool] = mapped_column(Boolean, default=False)
    comment_required_on_fail: Mapped[bool] = mapped_column(Boolean, default=False)
    photo_required_on_fail: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    template: Mapped["ChecklistTemplate"] = relationship(back_populates="questions")


# ---------------------------------------------------------------------------
# Inspections
# ---------------------------------------------------------------------------
class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=_new_uuid, index=True)

    template_id: Mapped[int] = mapped_column(ForeignKey("checklist_templates.id"))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))
    inspector_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"))

    # Free-text header captured at inspection time (kept even if asset changes).
    asset_number_text: Mapped[str | None] = mapped_column(String(60))
    registration_text: Mapped[str | None] = mapped_column(String(60))
    driver_operator: Mapped[str | None] = mapped_column(String(120))
    department_text: Mapped[str | None] = mapped_column(String(120))
    contractor_text: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[str | None] = mapped_column(String(120))
    meter_reading: Mapped[str | None] = mapped_column(String(40))

    # Visitor-vehicle specific header fields.
    vehicle_number: Mapped[str | None] = mapped_column(String(60))
    driver_name: Mapped[str | None] = mapped_column(String(120))
    contractor_company: Mapped[str | None] = mapped_column(String(120))
    host_department: Mapped[str | None] = mapped_column(String(120))
    alcohol_test_result: Mapped[str | None] = mapped_column(String(40))

    start_time: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completion_time: Mapped[datetime | None] = mapped_column(DateTime)
    result: Mapped[str | None] = mapped_column(String(40))
    general_comment: Mapped[str | None] = mapped_column(Text)
    sync_status: Mapped[str] = mapped_column(String(20), default="Draft")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    template: Mapped["ChecklistTemplate"] = relationship()
    asset: Mapped["Asset"] = relationship()
    inspector: Mapped["User"] = relationship()
    site: Mapped["Site"] = relationship()
    responses: Mapped[list["InspectionResponse"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )
    photos: Mapped[list["InspectionPhoto"]] = relationship(
        back_populates="inspection", cascade="all, delete-orphan"
    )


class InspectionResponse(Base):
    __tablename__ = "inspection_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("checklist_questions.id"))
    answer: Mapped[str | None] = mapped_column(String(10))  # Yes / No / N/A
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    inspection: Mapped["Inspection"] = relationship(back_populates="responses")
    question: Mapped["ChecklistQuestion"] = relationship()


class InspectionPhoto(Base):
    __tablename__ = "inspection_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"))
    response_id: Mapped[int | None] = mapped_column(ForeignKey("inspection_responses.id"))
    file_path: Mapped[str] = mapped_column(String(255))
    caption: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    inspection: Mapped["Inspection"] = relationship(back_populates="photos")


# ---------------------------------------------------------------------------
# Findings and corrective actions
# ---------------------------------------------------------------------------
class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    reference: Mapped[str] = mapped_column(String(36), unique=True, default=_new_uuid)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"))
    question_id: Mapped[int | None] = mapped_column(ForeignKey("checklist_questions.id"))
    checklist_name: Mapped[str | None] = mapped_column(String(120))
    failed_question_text: Mapped[str | None] = mapped_column(String(255))
    comment: Mapped[str | None] = mapped_column(Text)
    photo_path: Mapped[str | None] = mapped_column(String(255))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"))
    department_text: Mapped[str | None] = mapped_column(String(120))
    contractor_text: Mapped[str | None] = mapped_column(String(120))
    inspector_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    finding_date: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    is_no_go: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(30), default="Open")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    corrective_actions: Mapped[list["CorrectiveAction"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )


class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id"))
    description: Mapped[str] = mapped_column(Text)
    responsible_person: Mapped[str | None] = mapped_column(String(120))
    due_date: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="Open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    finding: Mapped["Finding"] = relationship(back_populates="corrective_actions")


# ---------------------------------------------------------------------------
# Synchronisation, notifications and audit
# ---------------------------------------------------------------------------
class SyncQueue(Base):
    __tablename__ = "sync_queue"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"))
    inspection_uuid: Mapped[str] = mapped_column(String(36), index=True)
    status: Mapped[str] = mapped_column(String(20), default="Pending Sync")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    inspection: Mapped["Inspection"] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str | None] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
