"""Service layer: business logic that the UI calls into.

The UI never talks to the database directly — it goes through these services so
the same logic can later be reused by the FastAPI synchronisation server.
"""
