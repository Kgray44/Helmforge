from __future__ import annotations

import ctypes
import os
import subprocess
import webbrowser
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from shared_core.models.runtime import InputStatus, OutputStatus, RuntimeMode, RuntimePreflightStatus
from shared_core.runtime.device_discovery import build_runtime_preflight_status
from shared_core.runtime.setup_guidance import (
    OFFICIAL_THRUSTMASTER_SUPPORT_PAGE,
    SetupStatusLabel,
    build_setup_status_labels,
)


THRUSTMASTER_DRIVER_DOWNLOAD_URL = (
    "https://ts.thrustmaster.com/download/pub/webupdate/TFlightHotas/2025_TFHT_5.exe"
)
THRUSTMASTER_DRIVER_PACKAGE_NAME = "Drivers - Package 2025_TFHT_5 + Firmware"
VJOY_SETUP_SOURCE_URL = "https://github.com/BrunnerInnovation/vJoy/releases"
VJOY_LATEST_COMPATIBILITY_NOTE = (
    "Use a current signed Windows 10/11-compatible vJoy installer from the verified release source."
)


@dataclass(frozen=True)
class UrlOpenResult:
    url: str
    opened: bool
    message: str


@dataclass(frozen=True)
class InstallerLaunchDecision:
    launch_requested: bool
    user_confirmed: bool
    launch_permitted: bool
    installer_paths: tuple[str, ...] = ()
    installer_launched: bool = False
    admin_active: bool = False
    admin_permission_requested: bool = False
    reboot_may_be_required: bool = False
    messages: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class LocalDriverSetupStatus:
    preflight: RuntimePreflightStatus
    labels: tuple[SetupStatusLabel, ...]
    hotas_detected: bool
    vjoy_detected: bool
    simulation_mode_active: bool
    full_live_runtime_ready: bool
    admin_active: bool
    reboot_may_be_required: bool
    fatal_errors: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class InstalledSoftwareDetection:
    detected: bool
    display_names: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


def is_running_as_admin() -> bool:
    if os.name != "nt":
        return False

    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def is_likely_thrustmaster_driver_software_name(display_name: str) -> bool:
    compact = display_name.lower().replace(".", "")
    return (
        ("tflight" in compact and "hotas" in compact and "driver" in compact)
        or ("thrustmaster" in compact and "flight" in compact)
    )


def detect_thrustmaster_driver_software() -> InstalledSoftwareDetection:
    if os.name != "nt":
        return InstalledSoftwareDetection(detected=False)

    try:
        import winreg
    except ImportError:  # pragma: no cover - Windows-only standard library guard
        return InstalledSoftwareDetection(detected=False)

    uninstall_roots = (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    )
    detected_names: list[str] = []
    errors: list[str] = []

    for root in uninstall_roots:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root) as root_key:
                for index in range(winreg.QueryInfoKey(root_key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(root_key, index)
                        with winreg.OpenKey(root_key, subkey_name) as subkey:
                            display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    except FileNotFoundError:
                        continue
                    except OSError:
                        continue

                    if is_likely_thrustmaster_driver_software_name(str(display_name)):
                        detected_names.append(str(display_name))
        except OSError as exc:
            errors.append(f"Driver software registry check failed for {root}: {exc}")

    unique_names = tuple(dict.fromkeys(detected_names))
    return InstalledSoftwareDetection(
        detected=bool(unique_names),
        display_names=unique_names,
        errors=tuple(errors),
    )


def open_setup_url(url: str, *, actually_open: bool = False) -> UrlOpenResult:
    if not actually_open:
        return UrlOpenResult(
            url=url,
            opened=False,
            message="URL open prepared; no browser was launched because actually_open=False.",
        )

    opened = bool(webbrowser.open(url))
    return UrlOpenResult(
        url=url,
        opened=opened,
        message="Browser launch requested." if opened else "Browser launch request failed.",
    )


def open_official_thrustmaster_support_page(*, actually_open: bool = False) -> UrlOpenResult:
    return open_setup_url(OFFICIAL_THRUSTMASTER_SUPPORT_PAGE, actually_open=actually_open)


def open_vjoy_setup_source(*, actually_open: bool = False) -> UrlOpenResult:
    return open_setup_url(VJOY_SETUP_SOURCE_URL, actually_open=actually_open)


def evaluate_installer_launch_request(
    *,
    launch_installers: bool = False,
    user_confirmed: bool = False,
    installer_paths: Iterable[str] = (),
    admin_active: bool | None = None,
) -> InstallerLaunchDecision:
    paths = tuple(str(path) for path in installer_paths)
    admin = is_running_as_admin() if admin_active is None else admin_active

    if not launch_installers:
        return InstallerLaunchDecision(
            launch_requested=False,
            user_confirmed=user_confirmed,
            launch_permitted=False,
            installer_paths=paths,
            admin_active=admin,
            messages=("Installer launch was not requested; no installer will run.",),
        )

    if not user_confirmed:
        return InstallerLaunchDecision(
            launch_requested=True,
            user_confirmed=False,
            launch_permitted=False,
            installer_paths=paths,
            admin_active=admin,
            messages=("Installer launch requires explicit interactive confirmation.",),
        )

    if not paths:
        return InstallerLaunchDecision(
            launch_requested=True,
            user_confirmed=True,
            launch_permitted=False,
            installer_paths=paths,
            admin_active=admin,
            errors=("No installer paths were supplied.",),
        )

    return InstallerLaunchDecision(
        launch_requested=True,
        user_confirmed=True,
        launch_permitted=True,
        installer_paths=paths,
        admin_active=admin,
        messages=(
            "Installer launch is permitted by explicit flag and confirmation, but this decision does not mark installation successful.",
        ),
    )


def launch_approved_installers(
    *,
    launch_installers: bool,
    user_confirmed: bool,
    installer_paths: Iterable[str],
    launcher: Callable[[str], None] | None = None,
) -> InstallerLaunchDecision:
    decision = evaluate_installer_launch_request(
        launch_installers=launch_installers,
        user_confirmed=user_confirmed,
        installer_paths=installer_paths,
    )
    if not decision.launch_permitted:
        return decision

    missing_paths = tuple(path for path in decision.installer_paths if not Path(path).exists())
    if missing_paths:
        return InstallerLaunchDecision(
            launch_requested=decision.launch_requested,
            user_confirmed=decision.user_confirmed,
            launch_permitted=False,
            installer_paths=decision.installer_paths,
            admin_active=decision.admin_active,
            errors=tuple(f"Installer path does not exist: {path}" for path in missing_paths),
        )

    launch = launcher or _default_installer_launcher
    launched: list[str] = []
    errors: list[str] = []
    for path in decision.installer_paths:
        try:
            launch(path)
            launched.append(path)
        except Exception as exc:  # pragma: no cover - defensive boundary
            errors.append(f"Installer launch failed for {path}: {exc}")

    return InstallerLaunchDecision(
        launch_requested=True,
        user_confirmed=True,
        launch_permitted=not errors,
        installer_paths=decision.installer_paths,
        installer_launched=bool(launched),
        admin_active=decision.admin_active,
        admin_permission_requested=False,
        reboot_may_be_required=bool(launched),
        messages=tuple(f"Installer launched: {path}" for path in launched),
        errors=tuple(errors),
    )


def _default_installer_launcher(path: str) -> None:
    subprocess.Popen([path], shell=False)


def build_local_driver_setup_status(
    preflight: RuntimePreflightStatus | None = None,
    *,
    thrustmaster_driver_detected: bool | None = None,
    reboot_may_be_required: bool = False,
    admin_active: bool | None = None,
) -> LocalDriverSetupStatus:
    status = preflight or build_runtime_preflight_status()
    labels = build_setup_status_labels(
        status,
        thrustmaster_driver_detected=thrustmaster_driver_detected,
    )
    hotas_detected = status.input.status is InputStatus.DETECTED
    vjoy_detected = status.output.status in {
        OutputStatus.VJOY_DETECTED,
        OutputStatus.OUTPUT_VERIFIED,
    }
    full_live_ready = (
        status.mode is RuntimeMode.FULL_LIVE
        and status.output.status is OutputStatus.OUTPUT_VERIFIED
        and status.live_output_writes_verified
    )
    return LocalDriverSetupStatus(
        preflight=status,
        labels=labels,
        hotas_detected=hotas_detected,
        vjoy_detected=vjoy_detected,
        simulation_mode_active=status.mode is RuntimeMode.SIMULATED,
        full_live_runtime_ready=full_live_ready,
        admin_active=is_running_as_admin() if admin_active is None else admin_active,
        reboot_may_be_required=reboot_may_be_required,
        fatal_errors=status.errors,
        messages=status.messages,
        warnings=status.warnings,
    )
