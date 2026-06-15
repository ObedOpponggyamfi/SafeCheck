"""Checklist template definitions for Phase One.

These Python definitions are loaded into the database by the seeder. At runtime
the application reads questions *from the database*, never from this module, so
new checklists can be added later without touching any inspection screen.

Each question is a ``(text, is_no_go)`` pair:

* ``is_no_go=True``  — a critical item. Failing it forces a "No Go" result and
  requires a comment.
* ``is_no_go=False`` — a normal item. Failing it gives "Requires Attention".
"""
from __future__ import annotations

from safecheck.core.enums import ResultMode

# Header fields collected for standard vehicle/machinery checklists. The asset
# number and registration are filled automatically from the selected asset.
STANDARD_HEADER = [
    {"attr": "driver_operator", "label": "Driver / Operator"},
    {"attr": "department_text", "label": "Department / Contractor"},
    {"attr": "location", "label": "Inspection location"},
    {"attr": "meter_reading", "label": "Kilometre / hour-meter reading"},
]

# Header fields collected for Visitor Vehicle checklists.
VISITOR_HEADER = [
    {"attr": "driver_name", "label": "Driver's name"},
    {"attr": "contractor_company", "label": "Contractor / company"},
    {"attr": "host_department", "label": "Visiting department / host"},
    {"attr": "alcohol_test_result", "label": "Alcohol-test result"},
]


LIGHT_VEHICLE = {
    "name": "Light Vehicle Inspection",
    "category": "Light Vehicle",
    "result_mode": ResultMode.STANDARD,
    "header": STANDARD_HEADER,
    "questions": [
        ("Valid driver's licence", True),
        ("Valid roadworthy certificate", True),
        ("Valid insurance", False),
        ("Foot brake and parking brake", True),
        ("Steering", True),
        ("Seat belts", True),
        ("Horn", False),
        ("Wipers", False),
        ("No fuel leakage", True),
        ("No oil leakage", False),
        ("No coolant leakage", False),
        ("Headlights", False),
        ("Brake lights", False),
        ("Indicators", False),
        ("Mirrors", False),
        ("Reverse alarm and reverse light", False),
        ("Tyres and wheel nuts", True),
        ("Windscreen", False),
        ("Spare tyre", False),
        ("Jack and wheel tools", False),
        ("Fire extinguisher", False),
        ("First-aid box", False),
        ("Reflective triangles", False),
        ("Vehicle is not overloaded", False),
        ("Load is properly secured", True),
        ("General body condition", False),
        ("Driver and passengers are wearing the required PPE", False),
    ],
}


VISITOR_VEHICLE = {
    "name": "Visitor Vehicle Inspection",
    "category": "Visitor Vehicle",
    "result_mode": ResultMode.VISITOR,
    "header": VISITOR_HEADER,
    "questions": [
        ("Valid driver's licence", True),
        ("Valid roadworthy certificate", True),
        ("Valid insurance", True),
        ("Foot brake and parking brake", True),
        ("Horn", True),
        ("Seat belts", True),
        ("Wipers", True),
        ("No oil leakage", True),
        ("Headlights, indicators, beacon and brake lights", False),
        ("Mirrors", False),
        ("Reverse alarm and reverse light", True),
        ("Tyres and wheel nuts", False),
        ("Jack and accessories", True),
        ("Windscreen", False),
        ("Spare tyre is available and serviceable", False),
        ("At least two reflective triangles are available", False),
        ("Fire extinguisher is available and serviceable", False),
        ("First-aid box is available and adequately stocked", False),
        ("Vehicle is not overloaded", False),
        ("Goods are properly stacked and secured", True),
        ("Wheel chocks are available", False),
        ("General body condition is satisfactory", False),
        ("Starter is functional", True),
        ("Driver and passengers are wearing appropriate PPE", False),
    ],
}


# Templates built in Phase One. Machinery templates are added in Phase Two.
PHASE_ONE_TEMPLATES = [LIGHT_VEHICLE, VISITOR_VEHICLE]


def header_for(result_mode: str) -> list[dict]:
    """Return the header-field descriptors for a given result mode."""
    if result_mode == ResultMode.VISITOR.value:
        return VISITOR_HEADER
    return STANDARD_HEADER
