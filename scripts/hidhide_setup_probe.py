from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


TARGET_VID = "044F"
TARGET_PID = "B68D"
TARGET_DEVICE_NAME = "Thrustmaster"
ARTIFACT_ROOT = Path("artifacts") / "runtime-hidhide-setup"
REPORT_PATH = Path("docs") / "HelmForge" / "runtime-usability-1e-hidhide-setup-visibility-proof-report.md"
HIDHIDE_VENDOR_LABEL = "official Nefarius HidHide"
KNOWN_CLIENT_NAMES = ("HidHideClient.exe", "HidHideConfigurationClient.exe")
KNOWN_CLI_NAMES = ("HidHideCLI.exe", "HidHideCli.exe")
GAME_OR_LAUNCHER_HINTS = ("steam", "dcs", "msfs", "x-plane", "xplane", "game.exe", "launcher.exe")


@dataclass(frozen=True)
class DeviceCandidate:
    name: str
    instance_path: str
    source: str = "windows"
    vendor_id: str = ""
    product_id: str = ""
    manufacturer: str = ""
    status: str = ""
    present: bool = True

    @property
    def normalized_vendor_id(self) -> str:
        return _normalize_hex_id(self.vendor_id or _extract_id(self.instance_path, "VID"))

    @property
    def normalized_product_id(self) -> str:
        return _normalize_hex_id(self.product_id or _extract_id(self.instance_path, "PID"))

    @property
    def vid_pid_label(self) -> str:
        if self.normalized_vendor_id and self.normalized_product_id:
            return f"VID_{self.normalized_vendor_id}&PID_{self.normalized_product_id}"
        return ""

    @property
    def is_vjoy(self) -> bool:
        text = f"{self.name} {self.instance_path} {self.manufacturer}".lower()
        return "vjoy" in text

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "instance_path": self.instance_path,
            "source": self.source,
            "vendor_id": self.normalized_vendor_id,
            "product_id": self.normalized_product_id,
            "vid_pid": self.vid_pid_label,
            "manufacturer": self.manufacturer,
            "status": self.status,
            "present": self.present,
            "is_vjoy": self.is_vjoy,
        }


@dataclass(frozen=True)
class HidHideDetection:
    installed: bool
    version: str = ""
    client_path: Path | None = None
    cli_path: Path | None = None
    install_locations: tuple[Path, ...] = ()
    registry_display_name: str = ""
    registry_publisher: str = ""
    winget_available: bool = False
    winget_package_id: str = ""
    winget_publisher: str = ""
    winget_search_output: str = ""
    reboot_required: bool = False
    detection_notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "installed": self.installed,
            "version": self.version,
            "client_path": str(self.client_path) if self.client_path else "",
            "cli_path": str(self.cli_path) if self.cli_path else "",
            "install_locations": [str(path) for path in self.install_locations],
            "registry_display_name": self.registry_display_name,
            "registry_publisher": self.registry_publisher,
            "winget_available": self.winget_available,
            "winget_package_id": self.winget_package_id,
            "winget_publisher": self.winget_publisher,
            "reboot_required": self.reboot_required,
            "detection_notes": list(self.detection_notes),
        }


@dataclass(frozen=True)
class DeviceSelection:
    hidden_devices: tuple[DeviceCandidate, ...]
    vjoy_devices: tuple[DeviceCandidate, ...]
    ambiguous_devices: tuple[DeviceCandidate, ...]
    hotas_groups: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "hidden_devices": [device.to_dict() for device in self.hidden_devices],
            "vjoy_devices": [device.to_dict() for device in self.vjoy_devices],
            "ambiguous_devices": [device.to_dict() for device in self.ambiguous_devices],
            "hotas_groups": {label: list(paths) for label, paths in self.hotas_groups.items()},
        }


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False

    @property
    def status(self) -> str:
        if self.timed_out:
            return "timeout"
        return "passed" if self.returncode == 0 else "failed"

    def to_dict(self) -> dict[str, object]:
        return {
            "command": list(self.command),
            "returncode": self.returncode,
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
        }


CommandRunner = Callable[..., CommandResult]


def build_detection_summary(detection: HidHideDetection) -> dict[str, object]:
    summary = {
        "hidhide": detection.to_dict() | {
            "action": "ready" if detection.installed else "install_required",
        },
        "install_guidance": _install_guidance(detection),
        "truth_boundaries": {
            "driver_install": "never_silent",
            "reboot": "never_silent",
            "untrusted_downloads": "not_used",
        },
    }
    return summary


def build_allowlist(
    *,
    sys_executable: Path | None = None,
    pythonw_path: Path | None = None,
    bridge_exe_path: Path | None = None,
    helmforge_exe_path: Path | None = None,
    extra_whitelist_apps: Iterable[Path] = (),
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    executable = Path(sys_executable or sys.executable)
    candidates.append(executable)
    if pythonw_path is not None:
        candidates.append(Path(pythonw_path))
    else:
        candidates.append(executable.with_name("pythonw.exe"))
    if bridge_exe_path is not None:
        candidates.append(Path(bridge_exe_path))
    if helmforge_exe_path is not None:
        candidates.append(Path(helmforge_exe_path))
    candidates.extend(Path(path) for path in extra_whitelist_apps)

    allowlist: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if _looks_like_target_game_or_launcher(candidate):
            continue
        try:
            resolved = candidate.resolve()
        except OSError:
            resolved = candidate
        if not resolved.exists() or not resolved.is_file():
            continue
        if resolved.suffix.lower() != ".exe":
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        allowlist.append(resolved)
    return tuple(allowlist)


def select_hidden_device_candidates(
    devices: Sequence[DeviceCandidate],
    *,
    target_vid: str = TARGET_VID,
    target_pid: str = TARGET_PID,
    target_device_name: str = TARGET_DEVICE_NAME,
) -> DeviceSelection:
    normalized_vid = _normalize_hex_id(target_vid)
    normalized_pid = _normalize_hex_id(target_pid)
    hidden: list[DeviceCandidate] = []
    vjoy: list[DeviceCandidate] = []
    ambiguous: list[DeviceCandidate] = []

    for device in devices:
        if device.is_vjoy:
            vjoy.append(device)
            continue
        matches_vid_pid = device.normalized_vendor_id == normalized_vid and device.normalized_product_id == normalized_pid
        if matches_vid_pid:
            hidden.append(device)
            continue
        if _name_matches_target(device, target_device_name):
            ambiguous.append(device)

    groups: dict[str, list[str]] = {}
    for device in hidden:
        label = device.vid_pid_label or f"VID_{normalized_vid}&PID_{normalized_pid}"
        groups.setdefault(label, []).append(device.instance_path)

    return DeviceSelection(
        hidden_devices=tuple(hidden),
        vjoy_devices=tuple(vjoy),
        ambiguous_devices=tuple(ambiguous),
        hotas_groups={label: tuple(paths) for label, paths in groups.items()},
    )


def build_configuration_plan(
    *,
    detection: HidHideDetection,
    devices: Sequence[DeviceCandidate],
    allowlisted_apps: Sequence[Path],
    dry_run: bool = False,
    apply: bool = False,
    configure: bool = False,
    confirm: bool = False,
    manual_only: bool = False,
    target_vid: str = TARGET_VID,
    target_pid: str = TARGET_PID,
    target_device_name: str = TARGET_DEVICE_NAME,
) -> dict[str, object]:
    selection = select_hidden_device_candidates(
        devices,
        target_vid=target_vid,
        target_pid=target_pid,
        target_device_name=target_device_name,
    )
    hidden_entries = [_hidden_entry(device) for device in selection.hidden_devices]
    vjoy_entries = [device.to_dict() for device in selection.vjoy_devices]
    allowlist = tuple(_unique_paths(allowlisted_apps))

    base: dict[str, object] = {
        "status": "plan_ready",
        "installed": detection.installed,
        "will_enable_device_hiding": False,
        "allowlisted_apps": [str(path) for path in allowlist],
        "target_game_allowlisted_by_default": False,
        "hidden_device_entries": hidden_entries,
        "ambiguous_device_entries": [device.to_dict() for device in selection.ambiguous_devices],
        "hotas_groups": {label: list(paths) for label, paths in selection.hotas_groups.items()},
        "vjoy": {
            "devices": vjoy_entries,
            "hidden": False,
            "must_remain_visible": True,
        },
        "automation": {
            "cli_path": str(detection.cli_path) if detection.cli_path else "",
            "programmatic_apply": False,
            "reason": "",
        },
        "safety": {
            "hide_by_vid_pid_only": True,
            "vjoy_never_hidden": True,
            "requires_allowlist_before_hiding": True,
            "requires_confirm_for_apply": True,
        },
    }

    if not detection.installed:
        base["status"] = "install_required"
        base["failure_reason"] = "HidHide is not installed or could not be verified."
        return base

    wants_mutation = bool(apply or configure)

    if wants_mutation and not confirm:
        base["status"] = "blocked_confirmation_required"
        base["failure_reason"] = "Configure/apply mode requires --confirm because HidHide changes driver/filter state."
        return base

    if selection.hidden_devices and not allowlist:
        base["status"] = "blocked_missing_allowlist"
        base["failure_reason"] = (
            "Refusing to hide the physical HOTAS until at least one Bridge/HOTAS-reading executable is allow-listed."
        )
        return base

    if not selection.hidden_devices:
        base["status"] = "no_hotas_candidates"
        base["failure_reason"] = f"No device instance matched VID_{_normalize_hex_id(target_vid)}&PID_{_normalize_hex_id(target_pid)}."
        return base

    if dry_run:
        base["status"] = "dry_run"
        base["automation"]["reason"] = "Dry run only; no HidHide settings changed."
        return base

    if wants_mutation:
        if manual_only or detection.cli_path is None:
            base["status"] = "manual_required"
            base["automation"]["reason"] = "No verified HidHide CLI/API contract is available in this environment."
            return base
        base["status"] = "manual_required_cli_contract_unverified"
        base["automation"]["reason"] = (
            "HidHide CLI was detected, but this probe does not guess CLI mutation syntax without a verified local contract."
        )
        return base

    return base


def build_manual_setup_steps(
    *,
    allowlisted_apps: Sequence[Path],
    hidden_devices: Sequence[DeviceCandidate],
    vjoy_devices: Sequence[DeviceCandidate] = (),
) -> str:
    lines = [
        "# Manual HidHide Setup Steps",
        "",
        "These steps are intentionally explicit because HidHide is a driver/filter configuration surface.",
        "",
        "1. Open HidHide Configuration Client.",
        "2. Applications tab:",
    ]
    if allowlisted_apps:
        for path in allowlisted_apps:
            lines.append(f"   - Add `{path}`.")
    else:
        lines.append("   - Stop: add the Bridge/Python/HelmForge executable before hiding any device.")
    lines.extend(
        [
            "3. Devices tab:",
            "   - Select only physical Thrustmaster HOTAS One entries matching `VID_044F&PID_B68D`.",
        ]
    )
    for device in hidden_devices:
        lines.append(f"   - Physical HOTAS candidate: `{device.name}` / `{device.instance_path}`.")
    if vjoy_devices:
        for device in vjoy_devices:
            lines.append(f"   - vJoy must remain visible; do not select vJoy entry `{device.name}` / `{device.instance_path}`.")
    else:
        lines.append("   - vJoy must remain visible; do not select vJoy.")
    lines.extend(
        [
            "4. In the client, enable device hiding.",
            "5. Reconnect the HOTAS if needed.",
            "6. Rerun:",
            "   `python scripts/hidhide_setup_probe.py --verify --real-hotas-check --real-vjoy-writes --confirm`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_game_readiness_checklist(
    *,
    hidhide_installed: bool,
    hidhide_enabled: bool,
    hotas_hidden: bool,
    vjoy_hidden: bool,
    allowlist_ready: bool,
    target_game_allowlisted: bool,
    bridge_detects_hotas: bool,
    vjoy_detected: bool,
    physical_input_reaches_bridge: bool,
    output_intent_changes: bool,
    vjoy_write_calls_accepted: bool,
) -> str:
    def mark(value: bool) -> str:
        return "[x]" if value else "[ ]"

    lines = [
        "# Game Readiness After HidHide",
        "",
        f"{mark(hidhide_installed)} 1. HidHide installed.",
        f"{mark(hidhide_enabled)} 2. HidHide enabled.",
        f"{mark(hotas_hidden)} 3. Physical HOTAS selected/hidden by VID/PID.",
        f"{mark(not vjoy_hidden)} 4. vJoy not hidden.",
        f"{mark(allowlist_ready)} 5. Bridge/Python/HelmForge executable allow-listed.",
        f"{mark(not target_game_allowlisted)} 6. Target game not allow-listed.",
        f"{mark(bridge_detects_hotas)} 7. Bridge still detects physical HOTAS.",
        f"{mark(vjoy_detected)} 8. vJoy detected.",
        f"{mark(physical_input_reaches_bridge)} 9. Physical HOTAS input reaches Bridge after hiding.",
        f"{mark(output_intent_changes)} 10. Runtime output intent changes.",
        f"{mark(vjoy_write_calls_accepted)} 11. vJoy write calls accepted.",
        "[ ] 12. Target game should bind to vJoy Device 1.",
        "[ ] 13. If the game sees both physical HOTAS and vJoy, double input may occur.",
        "[ ] 14. If HelmForge stops seeing HOTAS, allow-list is wrong.",
        "[ ] 15. If game does not see vJoy, vJoy may be hidden/disabled or game may need restart.",
        "[ ] 16. Reconnect HOTAS and restart game after changing HidHide settings if needed.",
        "[ ] 17. vJoy readback remains not implemented unless separately proven.",
        "",
        "Manual game-facing visibility checklist:",
        "- Open joy.cpl.",
        "- Confirm vJoy Device 1 appears.",
        "- Confirm physical Thrustmaster HOTAS does not appear to game-facing contexts after HidHide is enabled.",
        "- If both physical HOTAS and vJoy appear in the game, double input may occur.",
        "- Target game should bind to vJoy Device 1.",
        "- Do not bind the physical HOTAS directly when using HelmForge remapping.",
        "- If HelmForge stops seeing HOTAS, the allow-list is wrong.",
        "- If the game does not see vJoy, vJoy may be hidden, disabled, or the game may need restart.",
        "- Restart the game after changing HidHide settings.",
    ]
    return "\n".join(lines) + "\n"


def build_verification_report(
    *,
    detection: HidHideDetection,
    configuration: Mapping[str, Any],
    verification: Mapping[str, Any],
    artifact_dir: Path,
    install_result: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    install_status = str((install_result or {}).get("status") or ("already_installed" if detection.installed else "not_requested"))
    reboot_required = bool((install_result or {}).get("reboot_required") or detection.reboot_required)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "artifact_dir": str(artifact_dir),
        "hidhide": detection.to_dict(),
        "install": _jsonable(install_result or {"status": install_status, "reboot_required": reboot_required}),
        "configuration": _jsonable(configuration),
        "verification": _jsonable(verification),
        "sections": {
            "install_status": install_status,
            "physical_hotas_detection_proof": verification.get("bridge_physical_hotas", "not_run"),
            "hidhide_configuration_proof": configuration.get("status", "not_run"),
            "verification_status": _verification_status(verification),
            "reboot_status": "pending" if reboot_required or install_status == "pending_reboot" else "not_required",
            "vjoy_write_call_proof": verification.get("vjoy_write_call", "not_run"),
            "vjoy_readback_status": "not_implemented",
            "game_level_proof": verification.get("game_facing_visibility", "manual_checklist_only"),
        },
        "truth_boundaries": {
            "vjoy_write_call": "accepted_call_only",
            "vjoy_readback": "not_implemented",
            "game_level_verification": "manual_checklist_only_unless_observed",
            "bridge_visibility": "proves_allowlisted_HelmForge_path_only",
            "ordinary_application_visibility": "not_proven_without_non_whitelisted_observer_or_game",
        },
    }


def physical_hotas_detection_status(
    *,
    bridge_ok: bool,
    bridge_text: str,
    setup_ok: bool,
    setup_text: str,
) -> str:
    combined_text = f"{bridge_text}\n{setup_text}"
    if not bridge_ok and not setup_ok:
        return "failed"
    return _detected_status(True, combined_text, ("VID_044F&PID_B68D", "Thrustmaster", "HOTAS"))


def should_run_real_verification(configuration_status: str) -> bool:
    blocked_statuses = {
        "install_required",
        "manual_install_required",
        "install_failed",
        "install_unverified",
        "blocked_unverified_package",
        "blocked_missing_allowlist",
        "blocked_confirmation_required",
        "no_hotas_candidates",
        "pending_reboot",
        "manual_required",
        "manual_required_cli_contract_unverified",
    }
    return configuration_status not in blocked_statuses


def _verification_status(verification: Mapping[str, Any]) -> str:
    statuses = (
        verification.get("bridge_physical_hotas", "not_run"),
        verification.get("runtime_setup_dry_run", "not_run"),
        verification.get("physical_smoke_probe", "not_run"),
        verification.get("vjoy_write_call", "not_run"),
    )
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "not_run" for status in statuses):
        return "partial"
    return "passed"


def hidhide_install_requires_reboot(result: CommandResult) -> bool:
    text = f"{result.stdout}\n{result.stderr}".lower()
    return result.returncode in {3010, 1641} or "reboot" in text or "restart required" in text


def run_install_flow(
    *,
    detection: HidHideDetection,
    confirm: bool,
    command_runner: CommandRunner | None = None,
    redetect: Callable[[], HidHideDetection] | None = None,
) -> dict[str, object]:
    if command_runner is None:
        command_runner = _run_command
    if redetect is None:
        redetect = detect_hidhide
    if detection.installed:
        return {
            "status": "already_installed",
            "installed_during_this_phase": False,
            "install_command": [],
            "pre_install_detection": detection.to_dict(),
            "post_install_detection": detection.to_dict(),
            "reboot_required": detection.reboot_required,
            "message": "HidHide is already installed; not reinstalling.",
        }
    if not confirm:
        return {
            "status": "blocked_confirmation_required",
            "installed_during_this_phase": False,
            "install_command": [],
            "pre_install_detection": detection.to_dict(),
            "reboot_required": False,
            "message": "Install mode requires --confirm before running winget install.",
        }
    if not detection.winget_available:
        return {
            "status": "manual_install_required",
            "installed_during_this_phase": False,
            "install_command": [],
            "pre_install_detection": detection.to_dict(),
            "reboot_required": False,
            "message": "winget is unavailable; install from the official Nefarius/GitHub release or trusted package manager.",
        }

    search = command_runner(("winget", "search", "HidHide"), timeout_sec=45)
    package = _parse_winget_hidhide(search.stdout + search.stderr)
    if search.returncode != 0 or package.get("id") != "Nefarius.HidHide":
        return {
            "status": "blocked_unverified_package",
            "installed_during_this_phase": False,
            "install_command": [],
            "pre_install_detection": detection.to_dict(),
            "winget_search": search.to_dict(),
            "reboot_required": False,
            "message": "Refusing to install because winget did not verify exact package ID Nefarius.HidHide.",
        }

    install_command = ("winget", "install", "-e", "--id", "Nefarius.HidHide")
    install = command_runner(install_command, timeout_sec=900)
    if hidhide_install_requires_reboot(install):
        return {
            "status": "pending_reboot",
            "installed_during_this_phase": install.returncode in {0, 3010, 1641},
            "install_command": list(install_command),
            "pre_install_detection": detection.to_dict(),
            "winget_search": search.to_dict(),
            "winget_install": install.to_dict(),
            "reboot_required": True,
            "message": "HidHide installation requires a reboot. Reboot Windows, then rerun the verification command.",
        }
    if install.returncode != 0:
        return {
            "status": "install_failed",
            "installed_during_this_phase": False,
            "install_command": list(install_command),
            "pre_install_detection": detection.to_dict(),
            "winget_search": search.to_dict(),
            "winget_install": install.to_dict(),
            "reboot_required": False,
            "message": "winget install failed; no HidHide configuration was attempted.",
        }

    post_detection = redetect()
    status = "installed" if post_detection.installed else "install_unverified"
    return {
        "status": status,
        "installed_during_this_phase": post_detection.installed,
        "install_command": list(install_command),
        "pre_install_detection": detection.to_dict(),
        "post_install_detection": post_detection.to_dict(),
        "winget_search": search.to_dict(),
        "winget_install": install.to_dict(),
        "reboot_required": post_detection.reboot_required,
        "message": "HidHide installation completed and detection was rechecked."
        if post_detection.installed
        else "winget install completed, but HidHide could not be detected afterward.",
    }


def build_manual_install_required() -> str:
    return "\n".join(
        [
            "# Manual HidHide Install Required",
            "",
            "1. Install HidHide from the official Nefarius/GitHub release or a trusted package manager.",
            "2. Reboot Windows if prompted.",
            "3. Rerun:",
            "   `python scripts/hidhide_setup_probe.py --configure --verify --real-hotas-check --real-vjoy-writes --confirm`",
        ]
    ) + "\n"


def runtime_authority_violations(project_root: Path = PROJECT_ROOT) -> list[str]:
    scanned_roots = (
        project_root / "scripts" / "hidhide_setup_probe.py",
    )
    forbidden_prefixes = ("v3_app.pages", "v3_app.liquid", "v3_app.widgets", "PySide6")
    violations: list[str] = []
    for root in scanned_roots:
        if not root.exists():
            continue
        paths = (root,) if root.is_file() else tuple(root.rglob("*.py"))
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                imported = ""
                if isinstance(node, ast.ImportFrom):
                    imported = node.module or ""
                elif isinstance(node, ast.Import):
                    imported = node.names[0].name
                if imported and imported.startswith(forbidden_prefixes):
                    violations.append(f"{path.relative_to(project_root)} imports {imported}")
    return violations


def detect_hidhide(*, setup_guided: bool = False) -> HidHideDetection:
    path_hits = _detect_known_hidhide_paths()
    registry = _detect_registry_hidhide()
    winget_available = shutil.which("winget") is not None
    winget_package_id = ""
    winget_publisher = ""
    winget_output = ""
    notes: list[str] = []

    if setup_guided and winget_available:
        search = _run_command(("winget", "search", "HidHide"), timeout_sec=45)
        winget_output = search.stdout + search.stderr
        package = _parse_winget_hidhide(winget_output)
        winget_package_id = package.get("id", "")
        winget_publisher = package.get("publisher", "")
        if search.returncode != 0:
            notes.append("winget search did not complete successfully")

    client_path = _first_existing(path_hits["clients"])
    cli_path = _first_existing(path_hits["clis"])
    install_locations = tuple(sorted({path.parent for path in path_hits["clients"] + path_hits["clis"] if path.exists()}))
    registry_display = str(registry.get("display_name", ""))
    registry_publisher = str(registry.get("publisher", ""))
    version = str(registry.get("version", ""))
    installed = bool(client_path or cli_path or registry_display)

    return HidHideDetection(
        installed=installed,
        version=version,
        client_path=client_path,
        cli_path=cli_path,
        install_locations=install_locations,
        registry_display_name=registry_display,
        registry_publisher=registry_publisher,
        winget_available=winget_available,
        winget_package_id=winget_package_id,
        winget_publisher=winget_publisher,
        winget_search_output=winget_output,
        reboot_required=False,
        detection_notes=tuple(notes),
    )


def enumerate_windows_devices() -> tuple[DeviceCandidate, ...]:
    if os.name != "nt":
        return ()
    script = r"""
$ErrorActionPreference = "SilentlyContinue"
$devices = Get-CimInstance Win32_PnPEntity |
  Where-Object {
    ($_.PNPDeviceID -match 'VID_|VJOY|HID') -or
    ($_.Name -match 'vJoy|HOTAS|Thrustmaster|T-Flight')
  } |
  Select-Object Name, PNPDeviceID, Manufacturer, Status
$devices | ConvertTo-Json -Depth 4
"""
    result = _run_command(("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script), timeout_sec=45)
    if result.returncode != 0 or not result.stdout.strip():
        return ()
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ()
    if isinstance(payload, dict):
        rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        return ()
    devices: list[DeviceCandidate] = []
    for row in rows:
        instance_path = str(row.get("PNPDeviceID") or "")
        name = str(row.get("Name") or "")
        if not instance_path and not name:
            continue
        devices.append(
            DeviceCandidate(
                name=name,
                instance_path=instance_path,
                manufacturer=str(row.get("Manufacturer") or ""),
                status=str(row.get("Status") or ""),
                source="Win32_PnPEntity",
            )
        )
    return tuple(devices)


def run_verification(
    args: argparse.Namespace,
    artifact_dir: Path,
    *,
    command_runner: CommandRunner | None = None,
) -> dict[str, object]:
    if command_runner is None:
        command_runner = _run_command
    verification: dict[str, object] = {
        "bridge_physical_hotas": "not_run",
        "runtime_setup_dry_run": "not_run",
        "physical_smoke_probe": "not_run",
        "vjoy_write_call": "not_run",
        "game_facing_visibility": "manual_checklist_only",
        "vjoy_readback": "not_implemented",
        "commands": {},
    }
    if not args.verify:
        return verification

    bridge = command_runner((sys.executable, "-m", "bridge_app.main", "--status"), timeout_sec=45)
    setup = command_runner(
        ("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ".\\scripts\\runtime_setup_check.ps1", "-DryRun"),
        timeout_sec=60,
    )
    _write_text(artifact_dir / "bridge-status.txt", bridge.stdout + bridge.stderr)
    _write_text(artifact_dir / "runtime-setup-check.txt", setup.stdout + setup.stderr)
    verification["commands"] = {
        "bridge_status": bridge.to_dict(),
        "runtime_setup_check": setup.to_dict(),
    }
    bridge_text = f"{bridge.stdout}\n{bridge.stderr}"
    setup_text = f"{setup.stdout}\n{setup.stderr}"
    verification["bridge_physical_hotas"] = physical_hotas_detection_status(
        bridge_ok=bridge.returncode == 0,
        bridge_text=bridge_text,
        setup_ok=setup.returncode == 0,
        setup_text=setup_text,
    )
    verification["runtime_setup_dry_run"] = "passed" if setup.returncode == 0 else "failed"
    verification["runtime_setup_hotas_vid_pid"] = _first_line_containing(setup_text, "VID_044F&PID_B68D")
    verification["vjoy_detected"] = "detected" if "vjoy" in setup_text.lower() else "not_proven"

    if args.real_hotas_check:
        command = [
            sys.executable,
            "scripts/runtime_physical_hotas_smoke_probe.py",
            "--timeout-sec",
            str(args.timeout_sec),
            "--settle-sec",
            str(args.settle_sec),
            "--minimal",
        ]
        if args.real_vjoy_writes:
            command.append("--real-vjoy-writes")
        smoke = command_runner(tuple(command), timeout_sec=max(75, int(args.timeout_sec) + 30))
        _write_text(artifact_dir / "runtime-physical-hotas-smoke.txt", smoke.stdout + smoke.stderr)
        verification["physical_smoke_probe"] = "passed" if smoke.returncode == 0 else "failed"
        verification["commands"]["physical_smoke_probe"] = smoke.to_dict()  # type: ignore[index]

    if args.real_vjoy_writes:
        truth = command_runner((sys.executable, "scripts/runtime_truth_value_probe.py", "--real-vjoy-writes"), timeout_sec=120)
        _write_text(artifact_dir / "runtime-truth-value-real-vjoy.txt", truth.stdout + truth.stderr)
        verification["vjoy_write_call"] = "passed" if truth.returncode == 0 else "failed"
        verification["commands"]["runtime_truth_value_probe"] = truth.to_dict()  # type: ignore[index]

    return verification


def run_probe(args: argparse.Namespace) -> dict[str, object]:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = Path(args.output_dir) / stamp
    artifact_dir.mkdir(parents=True, exist_ok=True)

    detection = detect_hidhide(setup_guided=bool(args.setup_guided or args.install))
    install_result: dict[str, object] = {
        "status": "not_requested",
        "installed_during_this_phase": False,
        "install_command": [],
        "reboot_required": detection.reboot_required,
    }
    if args.install and not args.skip_install:
        install_result = run_install_flow(detection=detection, confirm=bool(args.confirm))
        post_detection = install_result.get("post_install_detection")
        if isinstance(post_detection, Mapping):
            detection = _detection_from_dict(post_detection)
    elif args.install and args.skip_install:
        install_result = {
            "status": "manual_install_required",
            "installed_during_this_phase": False,
            "install_command": [],
            "reboot_required": False,
            "message": "Install was requested with --skip-install; manual installation is required.",
        }
    devices = enumerate_windows_devices()
    allowlist = build_allowlist(
        sys_executable=Path(args.python_path) if args.python_path else Path(sys.executable),
        bridge_exe_path=Path(args.bridge_exe_path) if args.bridge_exe_path else None,
        helmforge_exe_path=Path(args.helmforge_exe_path) if args.helmforge_exe_path else None,
        extra_whitelist_apps=tuple(Path(path) for path in args.extra_whitelist_app),
    )

    detection_summary = build_detection_summary(detection)
    _write_json(artifact_dir / "hidhide-detection.json", detection_summary)
    _write_json(artifact_dir / "hidhide-install.json", install_result)
    _write_json(artifact_dir / "device-enumeration.json", [device.to_dict() for device in devices])

    if args.detect_only:
        payload = {
            "status": "detect_only",
            "artifact_dir": str(artifact_dir),
            "detection": detection_summary,
            "device_count": len(devices),
        }
        _write_json(artifact_dir / "summary.json", payload)
        return payload

    install_blockers = {
        "manual_install_required",
        "blocked_confirmation_required",
        "blocked_unverified_package",
        "install_failed",
        "install_unverified",
        "pending_reboot",
    }
    if str(install_result.get("status")) in install_blockers and not detection.installed:
        manual_install_path = artifact_dir / "manual-install-required.md"
        _write_text(manual_install_path, build_manual_install_required())
        configuration = {
            "status": install_result.get("status"),
            "failure_reason": install_result.get("message", ""),
            "allowlisted_apps": [str(path) for path in allowlist],
            "hidden_device_entries": [],
            "vjoy": {"hidden": False, "must_remain_visible": True, "devices": []},
            "target_game_allowlisted_by_default": False,
            "will_enable_device_hiding": False,
        }
        verification = {
            "bridge_physical_hotas": "not_run",
            "runtime_setup_dry_run": "not_run",
            "physical_smoke_probe": "not_run",
            "vjoy_write_call": "not_run",
            "game_facing_visibility": "manual_checklist_only",
            "vjoy_readback": "not_implemented",
            "commands": {},
        }
        report = build_verification_report(
            detection=detection,
            configuration=configuration,
            verification=verification,
            artifact_dir=artifact_dir,
            install_result=install_result,
        )
        report["artifact_files"] = {"manual_install_required": str(manual_install_path)}
        _write_json(artifact_dir / "summary.json", report)
        _write_text(artifact_dir / "hidhide-setup-report.md", _markdown_report(report, manual_install_path, manual_install_path))
        return report

    plan = build_configuration_plan(
        detection=detection,
        devices=devices,
        allowlisted_apps=allowlist,
        dry_run=bool(args.dry_run or not (args.apply or args.configure)),
        apply=bool(args.apply),
        configure=bool(args.configure),
        confirm=bool(args.confirm),
        manual_only=bool(args.manual_only),
        target_vid=args.target_vid,
        target_pid=args.target_pid,
        target_device_name=args.target_device_name,
    )
    _write_json(artifact_dir / "hidhide-configuration-plan.json", plan)

    hidden_devices = tuple(
        DeviceCandidate(name=str(entry.get("name", "")), instance_path=str(entry.get("instance_path", "")), source="plan")
        for entry in plan.get("hidden_device_entries", [])
        if isinstance(entry, dict)
    )
    selection = select_hidden_device_candidates(devices, target_vid=args.target_vid, target_pid=args.target_pid, target_device_name=args.target_device_name)
    manual_steps = build_manual_setup_steps(
        allowlisted_apps=allowlist,
        hidden_devices=hidden_devices or selection.hidden_devices,
        vjoy_devices=selection.vjoy_devices,
    )
    manual_steps_path = artifact_dir / "manual-hidhide-setup-steps.md"
    _write_text(manual_steps_path, manual_steps)

    verify_args = argparse.Namespace(**vars(args))
    if not should_run_real_verification(str(plan.get("status", ""))):
        if verify_args.real_hotas_check or verify_args.real_vjoy_writes:
            verify_args.real_verification_skip_reason = (
                "Skipped real HOTAS/vJoy-write verification because HidHide setup is not installed/configured safely yet."
            )
        verify_args.real_hotas_check = False
        verify_args.real_vjoy_writes = False
    verification = run_verification(verify_args, artifact_dir)
    skip_reason = getattr(verify_args, "real_verification_skip_reason", "")
    if skip_reason:
        verification["real_verification_skip_reason"] = skip_reason
    checklist = build_game_readiness_checklist(
        hidhide_installed=detection.installed,
        hidhide_enabled=plan.get("status") in {"configured", "applied", "validated"},
        hotas_hidden=bool(plan.get("hidden_device_entries")) and plan.get("status") in {"configured", "applied", "validated"},
        vjoy_hidden=False,
        allowlist_ready=bool(allowlist),
        target_game_allowlisted=False,
        bridge_detects_hotas=verification.get("bridge_physical_hotas") == "detected",
        vjoy_detected=verification.get("vjoy_detected") == "detected",
        physical_input_reaches_bridge=verification.get("physical_smoke_probe") == "passed",
        output_intent_changes=verification.get("physical_smoke_probe") == "passed",
        vjoy_write_calls_accepted=verification.get("vjoy_write_call") == "passed",
    )
    checklist_path = artifact_dir / "game-readiness-after-hidhide.md"
    _write_text(checklist_path, checklist)

    report = build_verification_report(
        detection=detection,
        configuration=plan,
        verification=verification,
        artifact_dir=artifact_dir,
        install_result=install_result,
    )
    report["artifact_files"] = {
        "manual_steps": str(manual_steps_path),
        "game_readiness_checklist": str(checklist_path),
    }
    _write_json(artifact_dir / "summary.json", report)
    _write_text(artifact_dir / "hidhide-setup-report.md", _markdown_report(report, manual_steps_path, checklist_path))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect, plan, and verify safe HidHide setup for HelmForge HOTAS filtering.")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--detect-only", action="store_true")
    parser.add_argument("--setup-guided", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--real-hotas-check", action="store_true")
    parser.add_argument("--real-vjoy-writes", action="store_true")
    parser.add_argument("--timeout-sec", type=float, default=60.0)
    parser.add_argument("--settle-sec", type=float, default=2.0)
    parser.add_argument("--target-vid", default=TARGET_VID)
    parser.add_argument("--target-pid", default=TARGET_PID)
    parser.add_argument("--target-device-name", default=TARGET_DEVICE_NAME)
    parser.add_argument("--bridge-exe-path", default="")
    parser.add_argument("--helmforge-exe-path", default="")
    parser.add_argument("--python-path", default="")
    parser.add_argument("--extra-whitelist-app", action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument("--manual-only", action="store_true")
    args = parser.parse_args()

    payload = run_probe(args)
    print(json.dumps(_brief_payload(payload), indent=2))
    status = payload.get("configuration", {}).get("status") if isinstance(payload.get("configuration"), dict) else payload.get("status")
    if status in {"blocked_confirmation_required", "blocked_missing_allowlist", "blocked_unverified_package", "install_failed"}:
        return 2
    return 0


def _normalize_hex_id(value: str) -> str:
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", str(value or ""))
    return cleaned.upper().zfill(4)[-4:] if cleaned else ""


def _extract_id(instance_path: str, prefix: str) -> str:
    match = re.search(rf"{prefix}_([0-9A-Fa-f]{{4}})", instance_path or "", flags=re.IGNORECASE)
    return match.group(1) if match else ""


def _name_matches_target(device: DeviceCandidate, target_device_name: str) -> bool:
    text = f"{device.name} {device.manufacturer}".lower()
    tokens = {target_device_name.lower(), "thrustmaster", "t-flight", "hotas"}
    return any(token and token in text for token in tokens)


def _hidden_entry(device: DeviceCandidate) -> dict[str, object]:
    data = device.to_dict()
    data["selection_reason"] = "matched_target_vid_pid_and_not_vjoy"
    return data


def _unique_paths(paths: Sequence[Path]) -> tuple[Path, ...]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        key = str(resolved).lower()
        if key not in seen:
            seen.add(key)
            unique.append(resolved)
    return tuple(unique)


def _looks_like_target_game_or_launcher(path: Path) -> bool:
    lower = str(path).lower()
    return any(hint in lower for hint in GAME_OR_LAUNCHER_HINTS)


def _install_guidance(detection: HidHideDetection) -> list[str]:
    if detection.installed:
        return ["HidHide appears installed; no install action is needed from this probe."]
    guidance = [
        f"Install {HIDHIDE_VENDOR_LABEL} from the verified Nefarius release/MSI or a verified package-manager source.",
    ]
    if detection.winget_available:
        if detection.winget_package_id == "Nefarius.HidHide":
            guidance.append("winget found Nefarius.HidHide; install manually with: winget install -e --id Nefarius.HidHide")
        else:
            guidance.append("winget is available; run winget search HidHide and verify package identity before installing.")
    else:
        guidance.append("winget was not detected; use the official Nefarius HidHide release/MSI and rerun --detect-only.")
    guidance.append("If the installer requires admin/UAC or reboot, complete that manually and rerun this probe after reboot.")
    return guidance


def _detect_known_hidhide_paths() -> dict[str, list[Path]]:
    roots = [value for value in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")) if value]
    vendors = (
        Path("Nefarius Software Solutions e.U") / "HidHide",
        Path("Nefarius Software Solutions") / "HidHide",
        Path("HidHide"),
    )
    suffixes = (Path("x64"), Path("x86"), Path(""))
    clients: list[Path] = []
    clis: list[Path] = []
    for root in roots:
        for vendor in vendors:
            for suffix in suffixes:
                base = Path(root) / vendor / suffix
                clients.extend(base / name for name in KNOWN_CLIENT_NAMES)
                clis.extend(base / name for name in KNOWN_CLI_NAMES)
    return {"clients": clients, "clis": clis}


def _detect_registry_hidhide() -> dict[str, str]:
    if os.name != "nt":
        return {}
    script = r"""
$ErrorActionPreference = "SilentlyContinue"
$roots = @(
  "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*",
  "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*"
)
$item = Get-ItemProperty $roots |
  Where-Object { $_.DisplayName -match "HidHide" } |
  Select-Object -First 1 DisplayName, DisplayVersion, Publisher, InstallLocation
$item | ConvertTo-Json -Depth 3
"""
    result = _run_command(("powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script), timeout_sec=30)
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        "display_name": str(payload.get("DisplayName") or ""),
        "version": str(payload.get("DisplayVersion") or ""),
        "publisher": str(payload.get("Publisher") or ""),
        "install_location": str(payload.get("InstallLocation") or ""),
    }


def _first_existing(paths: Sequence[Path]) -> Path | None:
    return next((path for path in paths if path.exists()), None)


def _parse_winget_hidhide(output: str) -> dict[str, str]:
    for line in output.splitlines():
        if "Nefarius.HidHide" in line:
            return {"id": "Nefarius.HidHide", "publisher": "Nefarius"}
    return {}


def _run_command(command: Sequence[str], *, timeout_sec: int | float) -> CommandResult:
    try:
        completed = subprocess.run(tuple(command), text=True, capture_output=True, timeout=timeout_sec)
        return CommandResult(tuple(command), completed.returncode, completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            tuple(command),
            124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
            timed_out=True,
        )
    except OSError as exc:
        return CommandResult(tuple(command), 127, stderr=str(exc))


def _detected_status(command_ok: bool, text: str, needles: Sequence[str]) -> str:
    if not command_ok:
        return "failed"
    lowered = text.lower()
    return "detected" if any(needle.lower() in lowered for needle in needles) else "not_detected"


def _first_line_containing(text: str, needle: str) -> str:
    lowered = needle.lower()
    for line in text.splitlines():
        if lowered in line.lower():
            return line.strip()
    return ""


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(payload), indent=2, sort_keys=True), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return value.to_dict()  # type: ignore[no-any-return]
    return value


def _detection_from_dict(payload: Mapping[str, object]) -> HidHideDetection:
    def path_or_none(value: object) -> Path | None:
        text = str(value or "")
        return Path(text) if text else None

    return HidHideDetection(
        installed=bool(payload.get("installed")),
        version=str(payload.get("version") or ""),
        client_path=path_or_none(payload.get("client_path")),
        cli_path=path_or_none(payload.get("cli_path")),
        install_locations=tuple(Path(str(path)) for path in payload.get("install_locations", []) if str(path)),
        registry_display_name=str(payload.get("registry_display_name") or ""),
        registry_publisher=str(payload.get("registry_publisher") or ""),
        winget_available=bool(payload.get("winget_available")),
        winget_package_id=str(payload.get("winget_package_id") or ""),
        winget_publisher=str(payload.get("winget_publisher") or ""),
        reboot_required=bool(payload.get("reboot_required")),
        detection_notes=tuple(str(note) for note in payload.get("detection_notes", [])),
    )


def _brief_payload(payload: Mapping[str, object]) -> dict[str, object]:
    if "sections" in payload:
        return {
            "artifact_dir": payload.get("artifact_dir"),
            "sections": payload.get("sections"),
            "configuration_status": payload.get("configuration", {}).get("status") if isinstance(payload.get("configuration"), dict) else "",
        }
    return dict(payload)


def _markdown_report(report: Mapping[str, object], manual_steps_path: Path, checklist_path: Path) -> str:
    sections = report.get("sections", {})
    configuration = report.get("configuration", {})
    hidhide = report.get("hidhide", {})
    lines = [
        "# Runtime Usability 1E HidHide Setup Artifact Report",
        "",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Artifact directory: `{report.get('artifact_dir', '')}`",
        f"- HidHide installed: `{hidhide.get('installed') if isinstance(hidhide, dict) else ''}`",
        f"- HidHide version: `{hidhide.get('version') if isinstance(hidhide, dict) else ''}`",
        f"- Configuration status: `{configuration.get('status') if isinstance(configuration, dict) else ''}`",
        f"- Physical HOTAS detection proof: `{sections.get('physical_hotas_detection_proof') if isinstance(sections, dict) else ''}`",
        f"- HidHide configuration proof: `{sections.get('hidhide_configuration_proof') if isinstance(sections, dict) else ''}`",
        f"- vJoy write-call proof: `{sections.get('vjoy_write_call_proof') if isinstance(sections, dict) else ''}`",
        "- vJoy readback status: `not_implemented`",
        f"- Game-level proof: `{sections.get('game_level_proof') if isinstance(sections, dict) else ''}`",
        f"- Manual steps: `{manual_steps_path}`",
        f"- Game readiness checklist: `{checklist_path}`",
        "",
        "This artifact report does not claim game-level filtering proof unless a non-whitelisted game/application was actually checked.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
