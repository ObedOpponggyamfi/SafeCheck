# SafeCheck Offline

An **offline-first safety inspection application** for vehicles, machinery and
workplaces. Field officers complete checklists on a Windows desktop (and later
Android) with **no internet required**; inspections are stored locally and
synchronised to a central server when a connection becomes available.

> Built with **Python only** — no React, JavaScript, Next.js, Supabase or
> Firebase. The whole stack is Python so the same codebase can target Windows
> today and Android later through Flet.

## The core experience

The field workflow is deliberately simple:

```
Open App → Select Checklist → Select Vehicle/Machine → Tick Yes / No / N/A
        → Comment on failed items → Submit
```

Colour language used throughout:

| Colour | Meaning            |
|--------|--------------------|
| 🟢 Green | Satisfactory       |
| 🟠 Amber | Requires attention |
| 🔴 Red   | No Go              |
| ⚪ Grey  | Not applicable     |

## Technology stack

| Concern                | Library                     |
|------------------------|-----------------------------|
| Application interface  | **Flet**                    |
| Local offline storage  | **SQLite**                  |
| Database management    | **SQLAlchemy**              |
| Synchronisation server | **FastAPI**                 |
| Client ⇄ server comms  | **HTTPX**                   |
| Photograph compression | **Pillow**                  |
| Excel reports          | **Pandas + OpenPyXL**       |
| PDF reports            | **ReportLab**               |
| Password security      | **Passlib + Bcrypt**        |

## Project structure

```
SafeCheck/
├── safecheck/              # Field application (Flet)
│   ├── config.py           # Paths and runtime constants
│   ├── core/               # Database engine, ORM models, enums, security
│   ├── data/               # Checklist definitions + demo-data seeding
│   ├── services/           # Business logic (auth, inspections, findings, sync)
│   └── ui/                 # Flet views (login, home, inspection, sync, history)
├── server/                 # FastAPI synchronisation server (central SQLite DB)
├── tests/                  # Unit + server tests (14 tests)
├── run_app.py              # Launch the field application
├── run_server.py           # Launch the synchronisation server (port 8077)
├── requirements.txt
└── README.md
```

The schema is **data-driven**: checklist questions live in the database, not in
hard-coded screens, so every checklist (light vehicle, visitor vehicle, and all
machinery types) is rendered by the same Yes/No/N/A interface.

## Getting started

```powershell
# 1. (Optional) create a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install dependencies
python -m pip install -r requirements.txt

# 3. Launch the field application (creates and seeds the local database)
python run_app.py
```

### Synchronisation server (optional)

The field app works fully offline; submitted inspections wait in the **Pending
Sync** queue. To sync them to the central server, start it in a second terminal:

```powershell
python run_server.py        # serves on http://127.0.0.1:8077
```

Then press **Sync All** (or **Retry**) on the Pending Sync screen. Uploads are
idempotent by inspection UUID, so re-syncing never creates duplicates. API docs
are auto-generated at http://127.0.0.1:8077/docs.

### Demo users

All demo accounts use the password **`safecheck`**.

| Username   | Role           |
|------------|----------------|
| `admin`    | Administrator  |
| `manager`  | Safety Manager |
| `officer1` | Safety Officer |
| `officer2` | Safety Officer |
| `super`    | Supervisor     |
| `mechanic` | Mechanic       |
| `driver`   | Driver/Operator|

## Development phases

**Phase One (this build)**

- Login with hashed passwords
- Home screen with checklist + summary cards
- Light Vehicle and Visitor Vehicle checklists
- Asset selection and auto-captured inspector/date/time/site
- Yes / No / N/A answering with immediate auto-save to SQLite
- Failure comment + optional photograph
- Automatic result (Fit for Use / Requires Attention / No Go;
  Entry Approved / Entry Denied for visitors)
- Save Draft and Submit Inspection with validation
- Automatic findings for every failed item
- Pending Sync screen and Inspection History

**Phase Two (in progress)**

- ✅ Machinery checklists — Heavy Vehicle, Excavator, Wheel Loader, Bulldozer,
  Grader, Drill Rig, Forklift, Crane, Generator (9 types)
- ✅ FastAPI synchronisation server — auth, checklist/asset download, idempotent
  inspection upload, photo upload, confirmation, history, findings endpoints
- ⏳ Findings workflow screen + corrective actions
- ⏳ Dashboards
- ⏳ PDF / Excel reports

## Status

✅ Phase One complete. 🚧 Phase Two in progress (machinery checklists and the
sync server are done). The most important requirement is **simplicity for field
users**.
