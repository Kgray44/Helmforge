from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = (
    PROJECT_ROOT / "docs" / "HelmForge" / "phase-19a-full-product-acceptance-inventory.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase19a_acceptance_inventory_document_exists_and_has_matrix_contract():
    assert INVENTORY_PATH.exists()
    inventory = _read(INVENTORY_PATH)

    assert "# Phase 19A Full Product Acceptance Inventory" in inventory
    assert (
        "| Area | Prompt-book expectation | Current implementation status | Evidence / files | "
        "Test coverage | Runtime truth / safety notes | Remaining gaps | Acceptance status |"
    ) in inventory

    for status in ("Pass", "Partial", "Deferred Truthfully", "Blocked", "Not Applicable"):
        assert status in inventory


def test_phase19a_inventory_covers_required_product_areas():
    inventory = _read(INVENTORY_PATH)

    for area in (
        "App shell",
        "Runtime setup",
        "Mapping",
        "Modes / Base Tuning / Filtering / Combat Profile / Profiles",
        "Conditional Rules",
        "Effective Response Stack",
        "Live Monitor",
        "Helm",
        "Live Overlay",
        "Flight Recorder",
        "Help / Docs",
        "Perf / Diagnostics",
        "Packaging",
        "Layout / Performance",
        "Safety boundaries",
    ):
        assert area in inventory


def test_phase19a_inventory_records_runtime_and_packaging_truth():
    inventory = _read(INVENTORY_PATH)

    for required in (
        "Full Live Runtime Ready proof gate",
        "no fake readiness",
        "Telemetry remains the truth surface",
        "Simulation mode remains available",
        "vJoy detected does not equal output verified",
        "Physical input alone is not full readiness",
        "fake/test paths are not real readiness",
        "no Bridge lifecycle management",
        "no driver/vJoy installer launch",
        "packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250",
        "packaged smoke passed",
        "assets/app_icon.ico is missing",
        "ISCC.exe",
        "Inno compile",
        "Phase 19B",
    ):
        assert required in inventory


def test_phase19a_safety_boundary_inventory_stays_within_phase_scope():
    inventory = _read(INVENTORY_PATH)
    lower_inventory = inventory.casefold()

    for required in (
        "no game injection",
        "no graphics api hooking",
        "no cloud ai/llm",
        "no auto-save",
        "no fake output verification",
        "no fake full live runtime ready",
        "simulation mode remains available",
    ):
        assert required in lower_inventory

    for forbidden in (
        "StartBridge control added",
        "StopBridge control added",
        "RestartBridge control added",
        "driver installer launch added",
        "vJoy installer launch added",
        "real capture added",
        "video encoding added",
        "cloud AI added",
        "auto-save added",
    ):
        assert forbidden.casefold() not in lower_inventory
