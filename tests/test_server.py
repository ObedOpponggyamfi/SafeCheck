"""Tests for the FastAPI synchronisation server.

Uses an isolated temporary central database (via the SAFECHECK_CENTRAL_DB env
var) so it never touches real data. Run with pytest or directly.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Point the central DB at a throwaway file BEFORE importing the server.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["SAFECHECK_CENTRAL_DB"] = _tmp.name

from fastapi.testclient import TestClient  # noqa: E402

from server.main import app  # noqa: E402

PAYLOAD = {
    "uuid": "test-uuid-1",
    "template_name": "Light Vehicle Inspection",
    "result_mode": "standard",
    "inspector_username": "officer1",
    "asset_number": "LV-001",
    "result": "No Go",
    "responses": [
        {"question_text": "Valid driver's licence", "answer": "No",
         "comment": "Licence expired", "is_no_go": True},
        {"question_text": "Horn", "answer": "Yes", "is_no_go": False},
    ],
}


def test_health_and_auth():
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        ok = client.post("/api/auth/login", json={"username": "officer1", "password": "safecheck"})
        assert ok.status_code == 200 and ok.json()["username"] == "officer1"
        bad = client.post("/api/auth/login", json={"username": "officer1", "password": "nope"})
        assert bad.status_code == 401


def test_downloads():
    with TestClient(app) as client:
        checklists = client.get("/api/checklists").json()
        assert len(checklists) == 11  # 2 Phase One + 9 machinery
        assets = client.get("/api/assets").json()
        assert any(a["asset_number"] == "EX-001" for a in assets)


def test_upload_is_idempotent_and_raises_findings():
    with TestClient(app) as client:
        first = client.post("/api/inspections", json=PAYLOAD)
        assert first.status_code == 201
        assert first.json()["status"] == "created"
        assert first.json()["findings_created"] == 1

        # Same UUID again -> duplicate, no new record.
        again = client.post("/api/inspections", json=PAYLOAD)
        assert again.status_code == 200
        assert again.json()["status"] == "duplicate"

        history = client.get("/api/inspections").json()
        assert sum(1 for i in history if i["uuid"] == "test-uuid-1") == 1

        # Confirmation endpoint and findings list.
        assert client.get("/api/inspections/test-uuid-1").json()["received"] is True
        findings = client.get("/api/findings").json()
        assert any(f["failed_question"] == "Valid driver's licence" for f in findings)


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    try:
        for test in tests:
            test()
            print(f"  PASS  {test.__name__}")
        print(f"\n{len(tests)}/{len(tests)} tests passed.")
    finally:
        try:
            os.unlink(_tmp.name)
        except OSError:
            pass


if __name__ == "__main__":
    _run_all()
