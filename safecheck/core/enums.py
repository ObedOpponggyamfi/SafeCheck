"""Enumerations shared across the database, services and UI layers.

Defining these once avoids magic strings scattered through the codebase. Each
enum subclasses ``str`` so the values store cleanly as text in SQLite and are
easy to display in the Flet interface.
"""
from __future__ import annotations

from enum import Enum


class AnswerType(str, Enum):
    """Possible answers for a single checklist question."""

    YES = "Yes"    # Satisfactory
    NO = "No"      # Not satisfactory
    NA = "N/A"     # Question does not apply


class InspectionResult(str, Enum):
    """System-generated overall result of an inspection.

    The first three values apply to standard checklists; the last two apply to
    Visitor Vehicle checklists.
    """

    FIT_FOR_USE = "Fit for Use"
    REQUIRES_ATTENTION = "Requires Attention"
    NO_GO = "No Go"
    ENTRY_APPROVED = "Entry Approved"
    ENTRY_DENIED = "Entry Denied"


class ResultMode(str, Enum):
    """How an inspection's result should be calculated."""

    STANDARD = "standard"   # Fit for Use / Requires Attention / No Go
    VISITOR = "visitor"     # Entry Approved / Entry Denied


class SyncStatus(str, Enum):
    """Lifecycle of an inspection within the synchronisation queue."""

    DRAFT = "Draft"
    PENDING_SYNC = "Pending Sync"
    UPLOADING = "Uploading"
    SYNCED = "Synced"
    SYNC_FAILED = "Sync Failed"


class FindingStatus(str, Enum):
    """Lifecycle of a finding raised from a failed checklist item."""

    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    PENDING_VERIFICATION = "Pending Verification"
    CLOSED = "Closed"
