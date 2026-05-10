from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN_DOC = ROOT / "docs" / "HelmForge" / "hf-lrdc-3a-low-latency-telemetry-transport-design.md"
REPORT_DOC = ROOT / "docs" / "HelmForge" / "hf-lrdc-3a-low-latency-telemetry-transport-report.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_hf_lrdc_3a_design_doc_exists_and_compares_required_transports():
    text = _read(DESIGN_DOC)

    for required in (
        "JSON snapshot file",
        "localhost WebSocket",
        "localhost TCP socket",
        "Windows named pipe",
        "memory-mapped file",
        "shared memory ring buffer",
        "hybrid stream primary + JSON diagnostic fallback",
    ):
        assert required in text

    for comparison_axis in (
        "latency",
        "jitter",
        "implementation complexity",
        "packaging impact",
        "dependency impact",
        "Windows compatibility",
        "cross-platform potential",
        "local-only safety",
        "firewall",
        "multiple UI client",
        "Bridge restart",
        "UI reconnect",
        "schema evolution",
        "testability",
        "human-debuggability",
        "failure modes",
        "30 Hz",
        "60 Hz",
        "120 Hz",
        "command/control",
        "large history",
    ):
        assert comparison_axis in text


def test_hf_lrdc_3a_design_selects_specific_transport_and_preserves_truth_boundaries():
    text = _read(DESIGN_DOC)

    assert "Recommended path for HF-LRDC-3B: localhost WebSocket stream primary" in text
    assert "JSON snapshot remains the diagnostic and fallback snapshot" in text
    assert "helmforge.telemetry_frame.v1" in text
    assert "A telemetry stream connection is not proof of vJoy writes" in text
    assert "Fresh telemetry is not proof of output verification" in text
    assert "The UI is not in the fast output path" in text
    assert "Do not implement the actual WebSocket server/client in HF-LRDC-3A" in text


def test_hf_lrdc_3a_report_documents_recommendation_fallback_and_deferred_work():
    text = _read(REPORT_DOC)

    assert "Final recommended transport: localhost WebSocket stream primary" in text
    assert "JSON fallback role" in text
    assert "Source priority" in text
    assert "HF-LRDC-3B" in text
    assert "runtime truth preservation" in text
    assert "no fake output verification" in text


def test_hf_lrdc_3a_source_priority_helper_prefers_stream_then_json_then_simulation():
    from shared_core.runtime.telemetry_transport import (
        TelemetrySourceCandidate,
        TelemetrySourceKind,
        TelemetryTransportState,
        select_telemetry_source,
    )

    simulation = TelemetrySourceCandidate(
        source=TelemetrySourceKind.SIMULATION_FALLBACK,
        state=TelemetryTransportState.FALLBACK,
        fresh=True,
        valid=True,
    )
    json_snapshot = TelemetrySourceCandidate(
        source=TelemetrySourceKind.BRIDGE_JSON_SNAPSHOT,
        state=TelemetryTransportState.CONNECTED,
        fresh=True,
        valid=True,
    )
    stream = TelemetrySourceCandidate(
        source=TelemetrySourceKind.BRIDGE_STREAM,
        state=TelemetryTransportState.CONNECTED,
        fresh=True,
        valid=True,
    )

    assert select_telemetry_source([simulation, json_snapshot, stream]) == stream
    assert select_telemetry_source([simulation, json_snapshot]) == json_snapshot
    assert select_telemetry_source([simulation]) == simulation


def test_hf_lrdc_3a_source_priority_rejects_stale_or_invalid_bridge_sources():
    from shared_core.runtime.telemetry_transport import (
        TelemetrySourceCandidate,
        TelemetrySourceKind,
        TelemetryTransportKind,
        TelemetryTransportState,
        select_telemetry_source,
    )

    stale_stream = TelemetrySourceCandidate(
        source=TelemetrySourceKind.BRIDGE_STREAM,
        state=TelemetryTransportState.STALE,
        fresh=False,
        valid=True,
    )
    invalid_json = TelemetrySourceCandidate(
        source=TelemetrySourceKind.BRIDGE_JSON_SNAPSHOT,
        state=TelemetryTransportState.INVALID,
        fresh=True,
        valid=False,
    )
    simulation = TelemetrySourceCandidate(
        source=TelemetrySourceKind.SIMULATION_FALLBACK,
        state=TelemetryTransportState.FALLBACK,
        fresh=True,
        valid=True,
    )

    assert TelemetryTransportKind.LOCAL_WEBSOCKET.value == "local_websocket"
    assert select_telemetry_source([stale_stream, invalid_json, simulation]) == simulation
