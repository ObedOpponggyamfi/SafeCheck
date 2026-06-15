"""SafeCheck Offline — offline-first safety inspection application.

The :mod:`safecheck` package contains the Flet field application. It is split
into four layers:

* :mod:`safecheck.core`     — database engine, ORM models, enums, security
* :mod:`safecheck.data`     — checklist definitions and demo-data seeding
* :mod:`safecheck.services` — business logic (auth, inspections, findings, sync)
* :mod:`safecheck.ui`       — Flet views and the application controller
"""

__version__ = "0.1.0"  # Phase One
