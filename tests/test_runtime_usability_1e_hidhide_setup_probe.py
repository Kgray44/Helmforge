from __future__ import annotations

import sys
from pathlib import Path

from scripts.hidhide_setup_probe import (
    CommandResult,
    DeviceCandidate,
    HidHideDetection,
    build_allowlist,
    build_configuration_plan,
    build_detection_summary,
    build_game_readiness_checklist,
    build_manual_setup_steps,
    build_verification_report,
    hidhide_install_requires_reboot,
    run_install_flow,
    run_verification,
    physical_hotas_detection_status,
    runtime_authority_violations,
    select_hidden_device_candidates,
    should_run_real_verification,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOTAS_PATH_1 = r"HID\VID_044F&PID_B68D&MI_00\7&11111111&0&0000"
HOTAS_PATH_2 = r"HID\VID_044F&PID_B68D&MI_01\7&22222222&0&0000"
VJOY_PATH = r"ROOT\VJOY\0000"


def _hotas(instance_path: str = HOTAS_PATH_1, *, name: str = "Thrustmaster T-Flight HOTAS One") -> DeviceCandidate:
    return DeviceCandidate(name=name, instance_path=instance_path, source="test")


def _vjoy(instance_path: str = VJOY_PATH, *, name: str = "vJoy Device 1") -> DeviceCandidate:
    return DeviceCandidate(name=name, instance_path=instance_path, source="test")


def test_detect_hidhide_missing_reports_install_needed_without_crash():
    summary = build_detection_summary(HidHideDetection(installed=False, winget_available=True))

    assert summary["hidhide"]["installed"] is False
    assert summary["hidhide"]["action"] == "install_required"
    assert "official Nefarius HidHide" in summary["install_guidance"][0]


def test_detect_hidhide_installed_reports_client_and_cli_paths():
    detection = HidHideDetection(
        installed=True,
        version="1.5.230",
        client_path=Path(r"C:\Program Files\Nefarius Software Solutions e.U\HidHide\x64\HidHideClient.exe"),
        cli_path=Path(r"C:\Program Files\Nefarius Software Solutions e.U\HidHide\x64\HidHideCLI.exe"),
    )

    summary = build_detection_summary(detection)

    assert summary["hidhide"]["installed"] is True
    assert summary["hidhide"]["version"] == "1.5.230"
    assert summary["hidhide"]["client_path"].endswith("HidHideClient.exe")
    assert summary["hidhide"]["cli_path"].endswith("HidHideCLI.exe")


def test_dry_run_selects_only_hotas_vid_pid_and_not_vjoy():
    devices = [
        _hotas(),
        _vjoy(),
        DeviceCandidate(name="Xbox Controller", instance_path=r"HID\VID_045E&PID_02FD\1", source="test"),
    ]

    plan = build_configuration_plan(
        detection=HidHideDetection(installed=True),
        devices=devices,
        allowlisted_apps=(Path(sys.executable),),
        dry_run=True,
    )

    assert plan["status"] == "dry_run"
    assert [entry["instance_path"] for entry in plan["hidden_device_entries"]] == [HOTAS_PATH_1]
    assert plan["vjoy"]["must_remain_visible"] is True
    assert plan["vjoy"]["hidden"] is False


def test_apply_refuses_to_hide_hotas_without_bridge_allowlist():
    plan = build_configuration_plan(
        detection=HidHideDetection(installed=True),
        devices=[_hotas()],
        allowlisted_apps=(),
        apply=True,
        confirm=True,
    )

    assert plan["status"] == "blocked_missing_allowlist"
    assert plan["will_enable_device_hiding"] is False
    assert "at least one Bridge/HOTAS-reading executable" in plan["failure_reason"]


def test_allowlist_includes_current_python_executable():
    allowlist = build_allowlist(sys_executable=Path(sys.executable))

    assert Path(sys.executable).resolve() in allowlist


def test_target_game_is_not_allowlisted_by_default():
    allowlist = build_allowlist(sys_executable=Path(sys.executable))
    lower = tuple(str(path).lower() for path in allowlist)

    assert not any("steam" in path for path in lower)
    assert not any("dcs" in path for path in lower)
    assert not any("game.exe" in path for path in lower)


def test_vjoy_is_never_added_to_hidden_devices():
    selected = select_hidden_device_candidates([_hotas(), _vjoy()])

    assert [device.instance_path for device in selected.hidden_devices] == [HOTAS_PATH_1]
    assert [device.instance_path for device in selected.vjoy_devices] == [VJOY_PATH]


def test_multiple_hotas_interfaces_are_grouped_by_vid_pid():
    selected = select_hidden_device_candidates([_hotas(HOTAS_PATH_1), _hotas(HOTAS_PATH_2)])

    assert len(selected.hidden_devices) == 2
    assert selected.hotas_groups == {
        "VID_044F&PID_B68D": (HOTAS_PATH_1, HOTAS_PATH_2),
    }


def test_manual_steps_include_applications_devices_enable_hiding_and_reconnect():
    steps = build_manual_setup_steps(
        allowlisted_apps=(Path(sys.executable),),
        hidden_devices=(_hotas(),),
        vjoy_devices=(_vjoy(),),
    )

    assert "Applications tab" in steps
    assert str(Path(sys.executable)) in steps
    assert "Devices tab" in steps
    assert "VID_044F&PID_B68D" in steps
    assert "do not select vJoy" in steps
    assert "enable device hiding" in steps
    assert "Reconnect the HOTAS" in steps


def test_verification_report_separates_hidhide_config_physical_proof_vjoy_write_call_and_game_manual_check():
    report = build_verification_report(
        detection=HidHideDetection(installed=True, version="1.5.230"),
        configuration={
            "status": "manual_required",
            "hidden_device_entries": [{"instance_path": HOTAS_PATH_1, "vid_pid": "VID_044F&PID_B68D"}],
            "allowlisted_apps": [str(Path(sys.executable))],
            "vjoy": {"hidden": False, "must_remain_visible": True},
        },
        verification={
            "bridge_physical_hotas": "not_run",
            "runtime_setup_dry_run": "not_run",
            "physical_smoke_probe": "not_run",
            "vjoy_write_call": "not_run",
            "game_facing_visibility": "manual_checklist_only",
        },
        artifact_dir=Path("artifacts/runtime-hidhide-setup/example"),
    )

    assert report["sections"]["physical_hotas_detection_proof"] == "not_run"
    assert report["sections"]["hidhide_configuration_proof"] == "manual_required"
    assert report["sections"]["vjoy_write_call_proof"] == "not_run"
    assert report["sections"]["vjoy_readback_status"] == "not_implemented"
    assert report["sections"]["game_level_proof"] == "manual_checklist_only"


def test_physical_hotas_detection_uses_runtime_setup_vid_pid_when_bridge_status_is_lifecycle_only():
    status = physical_hotas_detection_status(
        bridge_ok=True,
        bridge_text="HelmForge Bridge: lifecycle=LiveVerified truth=live_verified output_verified=True",
        setup_ok=True,
        setup_text="HOTAS match: HID-compliant game controller HID\\VID_044F&PID_B68D\\8&39EC0CDD&0&0000",
    )

    assert status == "detected"


def test_game_readiness_checklist_warns_about_double_input():
    checklist = build_game_readiness_checklist(
        hidhide_installed=True,
        hidhide_enabled=True,
        hotas_hidden=True,
        vjoy_hidden=False,
        allowlist_ready=True,
        target_game_allowlisted=False,
        bridge_detects_hotas=True,
        vjoy_detected=True,
        physical_input_reaches_bridge=True,
        output_intent_changes=True,
        vjoy_write_calls_accepted=True,
    )

    assert "Target game should bind to vJoy Device 1" in checklist
    assert "Open joy.cpl." in checklist
    assert "Do not bind the physical HOTAS directly when using HelmForge remapping." in checklist
    assert "Restart the game after changing HidHide settings." in checklist
    assert "If the game sees both physical HOTAS and vJoy, double input may occur." in checklist
    assert "vJoy readback remains not implemented unless separately proven." in checklist


def test_real_hotas_verification_is_skipped_when_hidhide_install_missing():
    assert should_run_real_verification("install_required") is False
    assert should_run_real_verification("blocked_missing_allowlist") is False
    assert should_run_real_verification("dry_run") is True


def test_no_ui_calculation_authority_imported():
    assert runtime_authority_violations(PROJECT_ROOT) == []


def test_install_mode_runs_winget_install_when_confirmed_and_package_id_verified():
    commands: list[tuple[str, ...]] = []

    def runner(command, *, timeout_sec):
        commands.append(tuple(command))
        if command[:3] == ("winget", "search", "HidHide"):
            return CommandResult(tuple(command), 0, stdout="HidHide  Nefarius.HidHide  1.5.230  winget\n")
        return CommandResult(tuple(command), 0, stdout="Successfully installed\n")

    result = run_install_flow(
        detection=HidHideDetection(installed=False, winget_available=True),
        confirm=True,
        command_runner=runner,
        redetect=lambda: HidHideDetection(installed=True, version="1.5.230"),
    )

    assert result["status"] == "installed"
    assert ("winget", "search", "HidHide") in commands
    assert ("winget", "install", "-e", "--id", "Nefarius.HidHide") in commands


def test_install_mode_refuses_without_confirm():
    commands: list[tuple[str, ...]] = []

    result = run_install_flow(
        detection=HidHideDetection(installed=False, winget_available=True),
        confirm=False,
        command_runner=lambda command, *, timeout_sec: commands.append(tuple(command)) or CommandResult(tuple(command), 0),
        redetect=lambda: HidHideDetection(installed=False),
    )

    assert result["status"] == "blocked_confirmation_required"
    assert commands == []


def test_install_mode_refuses_when_package_identity_unverified():
    commands: list[tuple[str, ...]] = []

    def runner(command, *, timeout_sec):
        commands.append(tuple(command))
        return CommandResult(tuple(command), 0, stdout="HidHide  Unknown.HidHide  1.0  winget\n")

    result = run_install_flow(
        detection=HidHideDetection(installed=False, winget_available=True),
        confirm=True,
        command_runner=runner,
        redetect=lambda: HidHideDetection(installed=False),
    )

    assert result["status"] == "blocked_unverified_package"
    assert ("winget", "install", "-e", "--id", "Nefarius.HidHide") not in commands


def test_install_mode_reports_reboot_required_and_stops():
    def runner(command, *, timeout_sec):
        if command[:3] == ("winget", "search", "HidHide"):
            return CommandResult(tuple(command), 0, stdout="HidHide  Nefarius.HidHide  1.5.230  winget\n")
        return CommandResult(tuple(command), 3010, stdout="Installation succeeded. Restart required.\n")

    result = run_install_flow(
        detection=HidHideDetection(installed=False, winget_available=True),
        confirm=True,
        command_runner=runner,
        redetect=lambda: HidHideDetection(installed=False),
    )

    assert result["status"] == "pending_reboot"
    assert result["reboot_required"] is True
    assert "requires a reboot" in result["message"]


def test_install_mode_rechecks_detection_after_success():
    redetect_calls = 0

    def runner(command, *, timeout_sec):
        if command[:3] == ("winget", "search", "HidHide"):
            return CommandResult(tuple(command), 0, stdout="HidHide  Nefarius.HidHide  1.5.230  winget\n")
        return CommandResult(tuple(command), 0, stdout="Successfully installed\n")

    def redetect():
        nonlocal redetect_calls
        redetect_calls += 1
        return HidHideDetection(installed=True, client_path=Path(r"C:\Program Files\Nefarius Software Solutions e.U\HidHide\x64\HidHideClient.exe"))

    result = run_install_flow(
        detection=HidHideDetection(installed=False, winget_available=True),
        confirm=True,
        command_runner=runner,
        redetect=redetect,
    )

    assert redetect_calls == 1
    assert result["post_install_detection"]["installed"] is True


def test_configure_after_install_hides_only_hotas_vid_pid():
    plan = build_configuration_plan(
        detection=HidHideDetection(installed=True),
        devices=[_hotas(), _hotas(HOTAS_PATH_2), _vjoy(), DeviceCandidate(name="Keyboard", instance_path=r"HID\VID_1532&PID_1234\1")],
        allowlisted_apps=(Path(sys.executable),),
        configure=True,
        confirm=True,
        manual_only=True,
    )

    assert plan["status"] == "manual_required"
    assert {entry["instance_path"] for entry in plan["hidden_device_entries"]} == {HOTAS_PATH_1, HOTAS_PATH_2}


def test_configure_after_install_keeps_vjoy_unhidden():
    plan = build_configuration_plan(
        detection=HidHideDetection(installed=True),
        devices=[_hotas(), _vjoy()],
        allowlisted_apps=(Path(sys.executable),),
        configure=True,
        confirm=True,
        manual_only=True,
    )

    assert plan["vjoy"]["hidden"] is False
    assert plan["vjoy"]["must_remain_visible"] is True


def test_configure_after_install_requires_bridge_or_python_allowlist():
    plan = build_configuration_plan(
        detection=HidHideDetection(installed=True),
        devices=[_hotas()],
        allowlisted_apps=(),
        configure=True,
        confirm=True,
    )

    assert plan["status"] == "blocked_missing_allowlist"
    assert plan["will_enable_device_hiding"] is False


def test_verify_after_install_runs_bridge_status_setup_check_and_physical_smoke_commands(tmp_path):
    commands: list[tuple[str, ...]] = []

    def runner(command, *, timeout_sec):
        commands.append(tuple(command))
        return CommandResult(tuple(command), 0, stdout="HOTAS match: HID\\VID_044F&PID_B68D\\1\nvJoy Device\n")

    args = type(
        "Args",
        (),
        {
            "verify": True,
            "real_hotas_check": True,
            "real_vjoy_writes": True,
            "timeout_sec": 60,
            "settle_sec": 2,
        },
    )()

    run_verification(args, tmp_path, command_runner=runner)

    assert any(command[:3] == (sys.executable, "-m", "bridge_app.main") for command in commands)
    assert any(any("runtime_setup_check.ps1" in part for part in command) for command in commands)
    assert any(any("scripts/runtime_physical_hotas_smoke_probe.py" in part for part in command) for command in commands)
    assert any(any("scripts/runtime_truth_value_probe.py" in part for part in command) for command in commands)


def test_report_distinguishes_installed_configured_verified_and_pending_reboot():
    report = build_verification_report(
        detection=HidHideDetection(installed=False, reboot_required=True),
        configuration={"status": "pending_reboot"},
        verification={"bridge_physical_hotas": "not_run", "vjoy_write_call": "not_run", "game_facing_visibility": "manual_checklist_only"},
        artifact_dir=Path("artifacts/runtime-hidhide-setup/example"),
        install_result={"status": "pending_reboot", "reboot_required": True},
    )

    assert report["sections"]["install_status"] == "pending_reboot"
    assert report["sections"]["hidhide_configuration_proof"] == "pending_reboot"
    assert report["sections"]["reboot_status"] == "pending"


def test_no_random_download_urls_are_used():
    source = (PROJECT_ROOT / "scripts" / "hidhide_setup_probe.py").read_text(encoding="utf-8").lower()

    assert "http://" not in source
    assert "https://" not in source
    assert "invoke-webrequest" not in source
    assert "curl " not in source


def test_no_device_manager_disable_path_exists():
    source = (PROJECT_ROOT / "scripts" / "hidhide_setup_probe.py").read_text(encoding="utf-8").lower()

    assert "disable-pnpdevice" not in source
    assert "devmgmt.msc" not in source
    assert "pnputil /disable-device" not in source
