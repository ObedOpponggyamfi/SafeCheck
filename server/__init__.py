"""SafeCheck synchronisation server (FastAPI).

A separate Python service with its own central SQLite database. The field
application uploads inspections here when internet is available; uploads are
idempotent by inspection UUID so the same inspection is never stored twice.
"""
