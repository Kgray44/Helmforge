from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESIGN_DOC = PROJECT_ROOT / "docs" / "HelmForge" / "phase-9g-bridge-lifecycle-ownership-design.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_phase9g_lifecycle_design_doc_covers_required_decision_anchors():
    text = _read(DESIGN_DOC)

    required_phrases = (
        "Phase 9G - Bridge Lifecycle Ownership Design",
        "Current Lifecycle State",
        "Option A: Manual Bridge Launch During Development",
        "Option B: UI-Launched Bridge Child Process",
        "Option C: Tray/Background Bridge Manager",
        "Option D: Windows Service",
        "Option E: Login Auto-Start Task",
        "Recommended Staged Lifecycle Path",
        "Bridge Lifecycle Truth States",
        "Future UI Wording Rules",
        "Safety Gates",
        "Design-Only Boundary",
    )
    for phrase in required_phrases:
        assert phrase in text


def test_phase9g_lifecycle_design_doc_names_truth_states_and_forbidden_claims():
    text = _read(DESIGN_DOC)

    for state in (
        "not_configured",
        "not_running",
        "starting",
        "running_simulated",
        "running_blocked_missing_device",
        "running_read_only",
        "running_live_unverified",
        "running_live_verified",
        "stopping",
        "crashed",
        "stale",
        "unknown",
    ):
        assert state in text

    for forbidden_claim in (
        "live",
        "active",
        "output verified",
        "ready",
        "connected to HOTAS",
        "writing to vJoy",
    ):
        assert forbidden_claim in text


def test_phase9g_existing_docs_reference_lifecycle_decision_without_claiming_implementation():
    for relative_path in (
        "docs/HelmForge/phase-ledger.md",
        "docs/HelmForge/bridge-service-design.md",
        "docs/HelmForge/bridge-ui-architecture.md",
    ):
        text = _read(PROJECT_ROOT / relative_path)
        assert "Phase 9G" in text
        assert "lifecycle ownership" in text.lower()
        assert "no lifecycle implementation" in text.lower() or "design-only" in text.lower()
