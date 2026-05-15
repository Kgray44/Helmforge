from __future__ import annotations

import os
from datetime import datetime, timezone


def _app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _telemetry(*, truth=None, output_verified: bool = False):
    from shared_core.models.runtime import AXIS_NAMES, BUTTON_NAMES, InputStatus, OutputStatus, RuntimeTruth
    from shared_core.runtime.bridge_lifecycle import BridgeLifecycleState
    from shared_core.runtime.telemetry import (
        AxisTelemetrySnapshot,
        BridgeTelemetrySnapshot,
        ButtonHatTelemetrySnapshot,
        ModeStateTelemetrySnapshot,
        OutputVerificationState,
        RuleStateSummary,
    )

    truth = truth or RuntimeTruth.DETECTED_UNVERIFIED
    raw = {axis: 0.1 for axis in AXIS_NAMES}
    return BridgeTelemetrySnapshot(
        runtime_truth=truth,
        lifecycle_state=BridgeLifecycleState.LIVE_VERIFIED if output_verified else BridgeLifecycleState.SIMULATED,
        input_status=InputStatus.DETECTED,
        output_status=OutputStatus.OUTPUT_VERIFIED if output_verified else OutputStatus.VJOY_DETECTED,
        raw_axes=AxisTelemetrySnapshot(raw),
        final_axes=AxisTelemetrySnapshot(raw),
        controls=ButtonHatTelemetrySnapshot(buttons={button: False for button in BUTTON_NAMES}, hats={}),
        active_modes=ModeStateTelemetrySnapshot(),
        timestamp=datetime.now(timezone.utc),
        active_profile="Perf 1A",
        rule_summary=RuleStateSummary(),
        output_verification=OutputVerificationState(verified=output_verified, backend_name="vJoy", message=""),
    )


def test_perf_1a_shell_chrome_updates_are_dirty_gated_and_truth_changes_are_immediate():
    from shared_core.models.runtime import RuntimeTruth
    from v3_app.ui.shell import HelmForgeShell

    _app()
    shell = HelmForgeShell()
    repeated = _telemetry()
    for _ in range(30):
        shell.apply_bridge_telemetry(repeated)

    assert shell.shell_chrome_update_count < 30
    assert shell.shell_chrome_skip_count > 0
    before = shell.shell_chrome_update_count

    shell.apply_bridge_telemetry(_telemetry(truth=RuntimeTruth.LIVE_VERIFIED, output_verified=True))

    assert shell.shell_chrome_update_count == before + 1
    assert shell.runtime_status.live_output_writes_verified is True
    assert shell._latest_bridge_telemetry is not None
