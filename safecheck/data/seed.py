"""Seed the local database with the Phase One demo data.

Demo data (per specification): three light vehicles, two visitor vehicles,
three drivers, two contractors, one site, four departments and two safety
officers, plus the Light Vehicle and Visitor Vehicle checklist templates.

Seeding is idempotent: organisation/user/asset data is created only when the
database is empty, while checklist templates are ensured on every start so the
question set stays current.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from safecheck.core import models
from safecheck.core.database import SessionLocal
from safecheck.core.security import hash_password
from safecheck.config import DEMO_PASSWORD
from safecheck.data.checklists import PHASE_ONE_TEMPLATES

# --- Reference data -------------------------------------------------------
ROLES = [
    ("Administrator", "Full system access"),
    ("Safety Manager", "Oversees safety programme"),
    ("Safety Officer", "Conducts and reviews inspections"),
    ("Supervisor", "Supervises field operations"),
    ("Mechanic", "Maintains vehicles and machinery"),
    ("Driver/Operator", "Operates vehicles and machinery"),
]

# (username, full_name, role_name, email)
USERS = [
    ("admin", "System Administrator", "Administrator", "admin@safecheck.local"),
    ("manager", "Mary Safety", "Safety Manager", "manager@safecheck.local"),
    ("officer1", "Kwabena Owusu", "Safety Officer", "officer1@safecheck.local"),
    ("officer2", "Akosua Danso", "Safety Officer", "officer2@safecheck.local"),
    ("super", "Samuel Supervisor", "Supervisor", "super@safecheck.local"),
    ("mechanic", "Michael Mensah", "Mechanic", "mechanic@safecheck.local"),
    ("driver", "Daniel Operator", "Driver/Operator", "driver@safecheck.local"),
    ("driver2", "Kwame Asante", "Driver/Operator", "driver2@safecheck.local"),
    ("driver3", "Ama Boateng", "Driver/Operator", "driver3@safecheck.local"),
]

SITE_NAME = "Ahafo Mine Site"
DEPARTMENTS = ["Mining", "Processing", "Engineering", "Logistics"]
CONTRACTORS = [("Rocksure Construction", "0244 000 111"), ("Geomine Services", "0209 222 333")]

# All asset categories (machinery included so Phase Two templates slot in).
ASSET_CATEGORIES = [
    "Light Vehicle", "Visitor Vehicle", "Heavy Vehicle", "Excavator",
    "Wheel Loader", "Bulldozer", "Grader", "Drill Rig", "Forklift",
    "Crane", "Generator",
]

# (asset_number, registration, description, category, department, contractor)
ASSETS = [
    ("LV-001", "GR-1234-20", "Toyota Hilux", "Light Vehicle", "Mining", None),
    ("LV-002", "GR-5678-21", "Ford Ranger", "Light Vehicle", "Engineering", None),
    ("LV-003", "GT-9012-22", "Nissan Navara", "Light Vehicle", "Logistics", None),
    ("VV-001", "AS-3344-19", "Toyota Corolla (Visitor)", "Visitor Vehicle", None, "Rocksure Construction"),
    ("VV-002", "WR-7788-23", "Hyundai H1 (Visitor)", "Visitor Vehicle", None, "Geomine Services"),
]


def _get_or_create(session: Session, model, defaults: dict | None = None, **filters):
    """Return an existing row matching *filters* or create a new one."""
    instance = session.scalars(select(model).filter_by(**filters)).first()
    if instance:
        return instance
    params = {**filters, **(defaults or {})}
    instance = model(**params)
    session.add(instance)
    session.flush()
    return instance


def _seed_reference_data(session: Session) -> None:
    """Seed roles, users, site, departments, contractors and assets."""
    roles = {name: _get_or_create(session, models.Role, name=name, defaults={"description": desc})
             for name, desc in ROLES}

    pwd = hash_password(DEMO_PASSWORD)
    for username, full_name, role_name, email in USERS:
        _get_or_create(
            session, models.User, username=username,
            defaults={
                "full_name": full_name,
                "email": email,
                "role_id": roles[role_name].id,
                "password_hash": pwd,
            },
        )

    site = _get_or_create(session, models.Site, name=SITE_NAME, defaults={"code": "AHF"})
    departments = {name: _get_or_create(session, models.Department, name=name,
                                        defaults={"site_id": site.id})
                   for name in DEPARTMENTS}
    contractors = {name: _get_or_create(session, models.Contractor, name=name,
                                        defaults={"contact": contact})
                   for name, contact in CONTRACTORS}
    categories = {name: _get_or_create(session, models.AssetCategory, name=name)
                  for name in ASSET_CATEGORIES}

    for number, reg, desc, cat, dept, contractor in ASSETS:
        _get_or_create(
            session, models.Asset, asset_number=number,
            defaults={
                "registration_number": reg,
                "description": desc,
                "category_id": categories[cat].id,
                "department_id": departments[dept].id if dept else None,
                "contractor_id": contractors[contractor].id if contractor else None,
            },
        )


def _seed_templates(session: Session) -> None:
    """Ensure every Phase One checklist template (and its questions) exists."""
    for spec in PHASE_ONE_TEMPLATES:
        category = _get_or_create(session, models.AssetCategory, name=spec["category"])
        existing = session.scalars(
            select(models.ChecklistTemplate).filter_by(name=spec["name"])
        ).first()
        if existing:
            continue  # Template already present — leave its questions untouched.

        template = models.ChecklistTemplate(
            name=spec["name"],
            category_id=category.id,
            result_mode=spec["result_mode"].value,
            description=f"{spec['name']} checklist",
        )
        session.add(template)
        session.flush()

        for order, (text, is_no_go) in enumerate(spec["questions"], start=1):
            session.add(models.ChecklistQuestion(
                template_id=template.id,
                text=text,
                display_order=order,
                is_mandatory=True,
                is_no_go=is_no_go,
                comment_required_on_fail=is_no_go,   # comment required for No Go items
                photo_required_on_fail=False,        # photographs optional in Phase One
            ))


def seed_all(session: Session | None = None) -> None:
    """Seed reference data (when empty) and ensure checklist templates exist."""
    own_session = session is None
    session = session or SessionLocal()
    try:
        already_seeded = session.scalars(select(models.User)).first() is not None
        if not already_seeded:
            _seed_reference_data(session)
        _seed_templates(session)
        session.commit()
    finally:
        if own_session:
            session.close()
