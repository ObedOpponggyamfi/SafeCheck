"""FastAPI synchronisation server.

Run with:  python run_server.py   (or: uvicorn server.main:app --reload)

Endpoints (per the specification):
* POST /api/auth/login              — user authentication
* GET  /api/checklists              — checklist download
* GET  /api/assets                  — asset download
* POST /api/inspections             — inspection upload (idempotent by UUID)
* POST /api/inspections/{uuid}/photos — photograph upload
* GET  /api/inspections/{uuid}      — synchronisation confirmation
* GET  /api/inspections             — inspection history
* GET  /api/findings                — findings
* GET  /api/corrective-actions      — corrective actions
"""
from __future__ import annotations

import uuid as uuidlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from safecheck import config
from safecheck.core import models
from safecheck.data.seed import seed_all
from safecheck.services import auth_service
from server.database import ServerSession, SERVER_PHOTOS_DIR, init_central_db
from server.schemas import InspectionUpload, LoginRequest, LoginResponse, UploadResult
from server.sync_store import store_inspection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create and seed the central database on startup."""
    init_central_db()
    session = ServerSession()
    try:
        seed_all(session)
    finally:
        session.close()
    yield


app = FastAPI(title="SafeCheck Sync Server", version="0.2.0", lifespan=lifespan)


def get_session():
    """Request-scoped central DB session."""
    session = ServerSession()
    try:
        yield session
    finally:
        session.close()


# --- Health ---------------------------------------------------------------
@app.get("/")
def root():
    return {"service": "SafeCheck Sync Server", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Auth -----------------------------------------------------------------
@app.post("/api/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    user = auth_service.authenticate(session, body.username, body.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return LoginResponse(
        id=user.id, username=user.username, full_name=user.full_name,
        role=user.role.name if user.role else None,
        token=uuidlib.uuid4().hex,  # opaque token (prototype; not yet validated)
    )


# --- Downloads ------------------------------------------------------------
@app.get("/api/checklists")
def checklists(session: Session = Depends(get_session)):
    templates = session.scalars(
        select(models.ChecklistTemplate).where(models.ChecklistTemplate.is_active.is_(True))
    ).all()
    return [
        {
            "id": t.id, "name": t.name, "result_mode": t.result_mode,
            "questions": [
                {
                    "text": q.text, "display_order": q.display_order,
                    "is_mandatory": q.is_mandatory, "is_no_go": q.is_no_go,
                    "comment_required_on_fail": q.comment_required_on_fail,
                }
                for q in t.questions
            ],
        }
        for t in templates
    ]


@app.get("/api/assets")
def assets(session: Session = Depends(get_session)):
    rows = session.scalars(select(models.Asset).where(models.Asset.is_active.is_(True))).all()
    return [
        {
            "id": a.id, "asset_number": a.asset_number,
            "registration_number": a.registration_number, "description": a.description,
            "category": a.category.name if a.category else None,
        }
        for a in rows
    ]


# --- Inspection upload + confirmation -------------------------------------
@app.post("/api/inspections", response_model=UploadResult)
def upload_inspection(payload: InspectionUpload, response: Response,
                      session: Session = Depends(get_session)):
    status, inspection, findings_created = store_inspection(session, payload)
    response.status_code = 200 if status == "duplicate" else 201
    return UploadResult(status=status, uuid=inspection.uuid, id=inspection.id,
                        findings_created=findings_created)


@app.get("/api/inspections/{inspection_uuid}")
def confirm_inspection(inspection_uuid: str, session: Session = Depends(get_session)):
    inspection = session.scalars(
        select(models.Inspection).where(models.Inspection.uuid == inspection_uuid)
    ).first()
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return {
        "uuid": inspection.uuid,
        "received": True,
        "result": inspection.result,
        "sync_status": inspection.sync_status,
    }


@app.post("/api/inspections/{inspection_uuid}/photos")
async def upload_photo(inspection_uuid: str, file: UploadFile,
                       session: Session = Depends(get_session)):
    inspection = session.scalars(
        select(models.Inspection).where(models.Inspection.uuid == inspection_uuid)
    ).first()
    if inspection is None:
        raise HTTPException(status_code=404, detail="Inspection not found")

    # Validate the upload: restricted types + size cap, and a safe generated
    # filename so a malicious client name can never escape the storage folder.
    ext = Path(file.filename or "").suffix.lower()
    if ext not in config.ALLOWED_PHOTO_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported photo type")
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Photo exceeds maximum size")

    # Use the inspection's stored UUID (not the raw path param) for the folder.
    target_dir = SERVER_PHOTOS_DIR / inspection.uuid
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuidlib.uuid4().hex}{ext}"
    target.write_bytes(data)

    photo = models.InspectionPhoto(inspection_id=inspection.id, file_path=str(target))
    session.add(photo)
    session.commit()
    return {"stored": str(target), "inspection_uuid": inspection.uuid}


# --- History, findings, corrective actions --------------------------------
@app.get("/api/inspections")
def inspection_history(session: Session = Depends(get_session)):
    rows = session.scalars(
        select(models.Inspection).order_by(models.Inspection.created_at.desc())
    ).all()
    return [
        {
            "uuid": i.uuid,
            "checklist": i.template.name if i.template else None,
            "asset_number": i.asset_number_text,
            "inspector": i.inspector.full_name if i.inspector else None,
            "result": i.result,
            "sync_status": i.sync_status,
            "completion_time": i.completion_time.isoformat() if i.completion_time else None,
        }
        for i in rows
    ]


@app.get("/api/findings")
def findings(session: Session = Depends(get_session)):
    rows = session.scalars(
        select(models.Finding).order_by(models.Finding.finding_date.desc())
    ).all()
    return [
        {
            "reference": f.reference, "checklist": f.checklist_name,
            "failed_question": f.failed_question_text, "comment": f.comment,
            "is_no_go": f.is_no_go, "status": f.status,
            "finding_date": f.finding_date.isoformat() if f.finding_date else None,
        }
        for f in rows
    ]


@app.get("/api/corrective-actions")
def corrective_actions(session: Session = Depends(get_session)):
    rows = session.scalars(select(models.CorrectiveAction)).all()
    return [
        {
            "id": c.id, "finding_id": c.finding_id, "description": c.description,
            "responsible_person": c.responsible_person, "status": c.status,
            "due_date": c.due_date.isoformat() if c.due_date else None,
        }
        for c in rows
    ]
