"""Launch the SafeCheck Offline field application.

Run with:  python run_app.py

On first launch this creates the local SQLite database and seeds the Phase One
demo data (users, vehicles, checklists). All demo accounts use the password
``safecheck`` — for example username ``officer1``.
"""
from __future__ import annotations

import flet as ft

from safecheck.core.database import init_db
from safecheck.data.seed import seed_all
from safecheck.ui.app import SafeCheckApp


def main(page: ft.Page) -> None:
    """Flet entry point — build the application controller and start it."""
    app = SafeCheckApp(page)
    app.start()


def _use_os_trust_store() -> None:
    """Route TLS verification through the OS trust store, if available.

    On corporate networks Flet's one-time client download can fail with
    ``CERTIFICATE_VERIFY_FAILED`` because an intercepting proxy CA is trusted by
    Windows but not by Python's bundled certificates. ``truststore`` delegates
    verification to the OS store (the same approach pip uses). It is optional —
    on a normal network the import simply does nothing.
    """
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:  # noqa: BLE001 — never block startup on this helper
        pass


def run() -> None:
    """Prepare the database, then launch the desktop window."""
    _use_os_trust_store()
    init_db()
    seed_all()
    ft.run(main)


if __name__ == "__main__":
    run()
