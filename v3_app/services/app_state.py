from __future__ import annotations

from dataclasses import dataclass, field

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimePreflightStatus, RuntimeTruth
from shared_core.models.workspace import CONFIG_FILENAME
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.driver_setup import detect_thrustmaster_driver_software


PAGE_IDS = (
    "mapping",
    "modes",
    "base_tuning",
    "filtering",
    "combat_profile",
    "profiles",
    "conditional_rules",
    "effective_response_stack",
    "live_monitor",
    "flight_recorder",
    "help_docs",
    "perf_diagnostics",
)


@dataclass
class RuntimeUiState:
    truth: RuntimeTruth
    input_status: InputStatus
    output_status: OutputStatus
    output_verified: bool
    driver_detected: bool = False
    backend_name: str | None = None

    @property
    def runtime_card_label(self) -> str:
        if self.truth is RuntimeTruth.LIVE_VERIFIED and self.output_verified:
            return "Live Verified"
        if self.truth is RuntimeTruth.DETECTED_UNVERIFIED:
            return "Output Unverified"
        if self.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
            return "HOTAS Not Connected"
        if self.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
            return "vJoy Missing" if self.output_status is OutputStatus.VJOY_MISSING else "Output Blocked"
        if self.truth is RuntimeTruth.ERROR:
            return "Runtime Error"
        return "Simulated"

    @property
    def header_truth_label(self) -> str:
        if self.truth is RuntimeTruth.LIVE_VERIFIED and self.output_verified:
            return "Live Verified"
        if self.truth is RuntimeTruth.DETECTED_UNVERIFIED:
            return "Detected Unverified"
        if self.truth is RuntimeTruth.BLOCKED_MISSING_DEVICE:
            return "Blocked Missing Device"
        if self.truth is RuntimeTruth.BLOCKED_MISSING_DRIVER:
            return "Blocked Missing Driver"
        if self.truth is RuntimeTruth.ERROR:
            return "Error"
        return "Simulated"

    @property
    def tone(self) -> str:
        if self.truth is RuntimeTruth.LIVE_VERIFIED and self.output_verified:
            return "success"
        if self.truth in {RuntimeTruth.DETECTED_UNVERIFIED, RuntimeTruth.SIMULATED}:
            return "caution"
        if self.truth is RuntimeTruth.ERROR:
            return "danger"
        return "warning"


@dataclass
class AppState:
    runtime: RuntimeUiState
    active_page_id: str = "mapping"
    selected_axis: str = "Roll"
    active_profile: str = "Current Workspace"
    source_config: str = CONFIG_FILENAME
    saved: bool = True
    status_message: str = "Workspace shell ready. Runtime truth is shown without claiming output writes."
    page_switch_timings_ms: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_runtime_status(
        cls,
        runtime_status: RuntimePreflightStatus,
        *,
        active_page_id: str = "mapping",
        driver_detected: bool = False,
    ) -> "AppState":
        return cls(
            runtime=RuntimeUiState(
                truth=runtime_status.truth,
                input_status=runtime_status.input.status,
                output_status=runtime_status.output.status,
                output_verified=runtime_status.live_output_writes_verified,
                driver_detected=driver_detected,
                backend_name=runtime_status.detected_output_backend_name,
            ),
            active_page_id=active_page_id,
        )


def build_initial_app_state() -> AppState:
    runtime_status = build_runtime_preflight_status()
    driver_detection = detect_thrustmaster_driver_software()
    return AppState.from_runtime_status(
        runtime_status,
        driver_detected=driver_detection.detected,
    )
