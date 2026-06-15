"""Phase Two machinery checklist templates.

Like the Phase One checklists, these are loaded into the database by the seeder
and rendered by the same Yes/No/N/A interface. Each question is a
``(text, is_no_go)`` pair. No-Go items force a "No Go" result and require a
comment when failed.

The mobile-plant machines (heavy vehicle, excavator, loader, dozer, grader,
drill rig) share a common pre-start base, then add machine-specific items.
Forklifts, cranes and generators have their own tailored lists.
"""
from __future__ import annotations

from safecheck.core.enums import ResultMode
from safecheck.data.checklists import STANDARD_HEADER


def _template(name: str, category: str, questions: list[tuple[str, bool]]) -> dict:
    return {
        "name": name,
        "category": category,
        "result_mode": ResultMode.STANDARD,
        "header": STANDARD_HEADER,
        "questions": questions,
    }


# Shared pre-start checks for mobile earth-moving / heavy plant.
_MOBILE_PLANT_BASE: list[tuple[str, bool]] = [
    ("Operator holds a valid licence / competency for this machine", True),
    ("Pre-start inspection completed and logbook signed", False),
    ("Seat belt fitted and serviceable", True),
    ("Service and parking brakes function correctly", True),
    ("Steering and operating controls function correctly", True),
    ("Emergency stop / battery isolator functional", True),
    ("Reverse alarm and reverse camera/light functional", True),
    ("Horn functional", False),
    ("Warning beacon / flashing light functional", False),
    ("Head, work and brake lights functional", False),
    ("Mirrors fitted, clean and correctly adjusted", False),
    ("No fuel leaks", True),
    ("No oil, hydraulic or coolant leaks", False),
    ("Hydraulic hoses, rams and fittings in good condition", False),
    ("ROPS/FOPS cab and all guards in place and intact", True),
    ("Fire extinguisher present, charged and serviceable", False),
    ("First-aid kit present and adequately stocked", False),
    ("Tyres / tracks and undercarriage in serviceable condition", False),
    ("Operator and ground crew wearing required PPE", False),
]


HEAVY_VEHICLE = _template("Heavy Vehicle Inspection", "Heavy Vehicle", _MOBILE_PLANT_BASE + [
    ("Valid roadworthy / inspection certificate", True),
    ("Load body / tray and tailgate secure", False),
    ("Body-up warning and hoist controls function correctly", True),
    ("Wheel nuts, rims and tyres serviceable (indicators in place)", True),
    ("Load is within limits and properly secured", True),
])

EXCAVATOR = _template("Excavator Inspection", "Excavator", _MOBILE_PLANT_BASE + [
    ("Bucket, teeth and pins secure and serviceable", False),
    ("Slew / swing brake and slew ring operate correctly", True),
    ("Quick-hitch (if fitted) locked and safety pin engaged", True),
    ("Track tension correct and track frame free of cracks", False),
])

WHEEL_LOADER = _template("Wheel Loader Inspection", "Wheel Loader", _MOBILE_PLANT_BASE + [
    ("Bucket / attachment and pins secure and serviceable", False),
    ("Articulation joint and lock bar in good condition", True),
    ("Bucket lift and tilt rams operate smoothly", False),
])

BULLDOZER = _template("Bulldozer Inspection", "Bulldozer", _MOBILE_PLANT_BASE + [
    ("Blade, rippers and pins secure and serviceable", False),
    ("Push-arms and lift cylinders in good condition", False),
    ("Undercarriage components and track tension serviceable", False),
])

GRADER = _template("Grader Inspection", "Grader", _MOBILE_PLANT_BASE + [
    ("Mouldboard / blade and circle assembly serviceable", False),
    ("Articulation and lean cylinders operate correctly", False),
    ("Scarifier / ripper teeth secure", False),
])

DRILL_RIG = _template("Drill Rig Inspection", "Drill Rig", _MOBILE_PLANT_BASE + [
    ("Mast / derrick structure and welds free of cracks", True),
    ("Drill string, rod handling and clamps serviceable", True),
    ("Wire ropes and sheaves in good condition", True),
    ("Dust suppression / collection system operational", False),
    ("Emergency stops at operator and ground level functional", True),
])


FORKLIFT = _template("Forklift Inspection", "Forklift", [
    ("Operator holds a valid forklift licence", True),
    ("Pre-start inspection completed", False),
    ("Service and parking brakes function correctly", True),
    ("Steering functions correctly", True),
    ("Horn functional", False),
    ("Reverse alarm and lights functional", True),
    ("Warning beacon functional", False),
    ("Seat belt fitted and serviceable", True),
    ("Mast, forks and carriage free of cracks and damage", True),
    ("Lift, lower and tilt functions operate smoothly", True),
    ("Lift chains evenly tensioned and serviceable", True),
    ("Load backrest extension fitted", False),
    ("Hydraulic system free of leaks", False),
    ("Tyres in serviceable condition", False),
    ("Data / capacity plate legible; rated capacity not exceeded", True),
    ("Overhead guard in place and intact", True),
    ("Fire extinguisher present and serviceable", False),
    ("Operator wearing required PPE", False),
])

CRANE = _template("Crane Inspection", "Crane", [
    ("Operator holds a valid crane operator licence / competency", True),
    ("Current crane inspection / load-test certificate available", True),
    ("Pre-start inspection completed and logbook signed", False),
    ("Load chart displayed and legible", True),
    ("Rated capacity indicator / limiter functional", True),
    ("Anti two-block device functional", True),
    ("Hook, safety latch and block in good condition", True),
    ("Wire ropes free of damage and correctly reeved", True),
    ("Outriggers, pads and lock pins serviceable", True),
    ("Slew, hoist and luffing brakes function correctly", True),
    ("Emergency stop functional", True),
    ("Boom / lattice and welds free of cracks or damage", True),
    ("Hydraulic system free of leaks", False),
    ("Warning beacon and horn functional", False),
    ("Fire extinguisher present and serviceable", False),
    ("Slings and lifting tackle inspected and within rating", True),
    ("Operator and riggers wearing required PPE", False),
])

GENERATOR = _template("Generator Inspection", "Generator", [
    ("Earth / grounding connection in place and secure", True),
    ("Pre-start inspection completed", False),
    ("Emergency stop functional", True),
    ("No fuel leaks", True),
    ("No oil or coolant leaks", False),
    ("Guards over rotating parts in place", True),
    ("Electrical panel closed and cables undamaged", True),
    ("RCD / earth-leakage protection functional", True),
    ("Exhaust system serviceable and routed away from people", False),
    ("Fire extinguisher present and serviceable", False),
    ("Fuel storage area clean and bunded", False),
    ("Adequate ventilation around the unit", False),
    ("Coolant and oil levels correct", False),
    ("Warning signage displayed", False),
    ("Operator wearing required PPE", False),
])


# All Phase Two machinery templates.
MACHINERY_TEMPLATES = [
    HEAVY_VEHICLE, EXCAVATOR, WHEEL_LOADER, BULLDOZER, GRADER,
    DRILL_RIG, FORKLIFT, CRANE, GENERATOR,
]
