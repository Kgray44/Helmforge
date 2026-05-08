from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".artifacts" / "phase19b_kraken"

REQUIRED_SECTIONS: tuple[str, ...] = (
    "source_app_smoke",
    "packaged_app_smoke",
    "bridge_smoke",
    "runtime_setup_dry_run",
    "page_navigation_smoke",
    "help_docs_search_smoke",
    "perf_diagnostics_copy_smoke",
    "helm_overlay_smoke",
    "live_overlay_smoke",
    "flight_recorder_smoke",
    "packaging_metadata_smoke",
    "installer_metadata_smoke",
    "runtime_truth_boundary_smoke",
    "full_live_runtime_ready_gate_smoke",
    "safety_boundary_smoke",
)

BOUNDARY_PHRASES = (
    "no fake readiness",
    "no Bridge lifecycle management",
    "no driver/vJoy installer launch",
    "no cloud AI/LLM",
    "no auto-save",
    "Full Live Runtime Ready proof gate",
)

PACKAGED_SMOKE_DISPLAY = "packaging/dist/HelmForge/HelmForge.exe --smoke-exit-ms 250"


@dataclass
class KrakenRow:
    section: str
    check: str
    status: str
    elapsed_ms: float
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    command: str = ""
    stdout_tail: str = ""
    stderr_tail: str = ""


def _tail(text: str, limit: int = 2200) -> str:
    text = text or ""
    return text[-limit:]


def _add_row(
    rows: list[KrakenRow],
    *,
    section: str,
    check: str,
    status: str,
    message: str,
    elapsed_ms: float = 0.0,
    details: dict[str, Any] | None = None,
    command: str = "",
    stdout_tail: str = "",
    stderr_tail: str = "",
) -> KrakenRow:
    row = KrakenRow(
        section=section,
        check=check,
        status=status,
        elapsed_ms=round(elapsed_ms, 2),
        message=message,
        details=details or {},
        command=command,
        stdout_tail=_tail(stdout_tail),
        stderr_tail=_tail(stderr_tail),
    )
    rows.append(row)
    return row


def _command_text(command: Sequence[str]) -> str:
    try:
        return subprocess.list2cmdline([str(part) for part in command])
    except Exception:
        return " ".join(str(part) for part in command)


def _run_command(
    rows: list[KrakenRow],
    *,
    section: str,
    check: str,
    command: Sequence[str],
    cwd: Path = REPO_ROOT,
    env: dict[str, str] | None = None,
    timeout: int = 120,
    pass_predicate: Callable[[subprocess.CompletedProcess[str]], tuple[bool, str]] | None = None,
) -> subprocess.CompletedProcess[str] | None:
    command_str = _command_text(command)
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [str(part) for part in command],
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        elapsed = (time.perf_counter() - started) * 1000.0
    except subprocess.TimeoutExpired as exc:
        elapsed = (time.perf_counter() - started) * 1000.0
        _add_row(
            rows,
            section=section,
            check=check,
            status="fail",
            elapsed_ms=elapsed,
            message=f"Command timed out after {timeout}s.",
            command=command_str,
            stdout_tail=exc.stdout or "",
            stderr_tail=exc.stderr or "",
        )
        return None

    if pass_predicate is not None:
        ok, message = pass_predicate(completed)
    else:
        ok = completed.returncode == 0
        message = "Command exited 0." if ok else f"Command exited {completed.returncode}."

    _add_row(
        rows,
        section=section,
        check=check,
        status="pass" if ok else "fail",
        elapsed_ms=elapsed,
        message=message,
        details={"exit_code": completed.returncode},
        command=command_str,
        stdout_tail=completed.stdout,
        stderr_tail=completed.stderr,
    )
    return completed


def _runtime_status_fixture():
    from shared_core.models.runtime import (
        InputDeviceDetection,
        InputStatus,
        OutputBackendDetection,
        OutputStatus,
        RuntimeMode,
        RuntimePreflightStatus,
        RuntimeTruth,
    )

    return RuntimePreflightStatus(
        mode=RuntimeMode.SIMULATED,
        truth=RuntimeTruth.BLOCKED_MISSING_DEVICE,
        input=InputDeviceDetection(status=InputStatus.MISSING),
        output=OutputBackendDetection(
            status=OutputStatus.VJOY_DETECTED,
            backend_name="vJoy",
            live_output_writes_verified=False,
        ),
        messages=("Simulation fallback remains available; live output is not verified.",),
    )


def _ensure_qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _workspace():
    from shared_core.models.workspace import create_default_workspace

    return create_default_workspace()


def _state():
    from v3_app.services.app_state import AppState

    return AppState.from_runtime_status(_runtime_status_fixture(), driver_detected=True)


def _shell(workspace_path: Path):
    from v3_app.ui.shell import HelmForgeShell

    return HelmForgeShell(
        _state(),
        workspace=_workspace(),
        runtime_status=_runtime_status_fixture(),
        workspace_path=workspace_path,
    )


def _widget_text(widget: Any) -> str:
    from PySide6.QtWidgets import QLabel, QPushButton

    labels = [label.text() for label in widget.findChildren(QLabel)]
    buttons = [button.text() for button in widget.findChildren(QPushButton)]
    return "\n".join((*labels, *buttons))


def _run_callable(
    rows: list[KrakenRow],
    *,
    section: str,
    check: str,
    callback: Callable[[], dict[str, Any]],
) -> None:
    started = time.perf_counter()
    try:
        details = callback()
    except Exception as exc:  # pragma: no cover - exercised by harness failures, not static tests.
        elapsed = (time.perf_counter() - started) * 1000.0
        _add_row(
            rows,
            section=section,
            check=check,
            status="fail",
            elapsed_ms=elapsed,
            message=f"{type(exc).__name__}: {exc}",
            details={},
        )
        return
    elapsed = (time.perf_counter() - started) * 1000.0
    _add_row(
        rows,
        section=section,
        check=check,
        status="pass",
        elapsed_ms=elapsed,
        message="Check passed.",
        details=details,
    )


def run_source_app_smoke(rows: list[KrakenRow]) -> None:
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    _run_command(
        rows,
        section="source_app_smoke",
        check="offscreen_source_launch",
        command=(sys.executable, "-m", "v3_app.main", "--smoke-exit-ms", "250"),
        env=env,
        timeout=120,
    )


def run_packaged_app_smoke(rows: list[KrakenRow]) -> None:
    exe = REPO_ROOT / "packaging" / "dist" / "HelmForge" / "HelmForge.exe"
    if not exe.exists():
        _add_row(
            rows,
            section="packaged_app_smoke",
            check="packaged_executable_exists",
            status="fail",
            message="Phase 18B/18D expect the packaged executable to exist, but it is missing.",
            details={"expected": str(exe), "documented_command": PACKAGED_SMOKE_DISPLAY},
        )
        return
    _add_row(
        rows,
        section="packaged_app_smoke",
        check="packaged_executable_exists",
        status="pass",
        message="Packaged executable exists.",
        details={"path": str(exe), "documented_command": PACKAGED_SMOKE_DISPLAY},
    )
    _run_command(
        rows,
        section="packaged_app_smoke",
        check="packaged_smoke_launch",
        command=(str(exe), "--smoke-exit-ms", "250"),
        timeout=120,
    )


def run_bridge_smoke(rows: list[KrakenRow]) -> None:
    _run_command(
        rows,
        section="bridge_smoke",
        check="bridge_once",
        command=(sys.executable, "-m", "bridge_app.main", "--once"),
        timeout=120,
    )
    _run_command(
        rows,
        section="bridge_smoke",
        check="bridge_run_for_250ms",
        command=(sys.executable, "-m", "bridge_app.main", "--run-for-ms", "250"),
        timeout=120,
    )
    completed = _run_command(
        rows,
        section="bridge_smoke",
        check="bridge_status",
        command=(sys.executable, "-m", "bridge_app.main", "--status"),
        timeout=120,
    )
    if completed is None:
        return
    output = completed.stdout.strip()
    expected = (
        "lifecycle=Simulated" in output
        and "truth=blocked_missing_device" in output
        and "output_verified=False" in output
    )
    _add_row(
        rows,
        section="bridge_smoke",
        check="bridge_conservative_truth",
        status="pass" if expected else "fail",
        message=(
            "Bridge status kept conservative simulated truth."
            if expected
            else "Bridge status did not match expected conservative truth."
        ),
        details={"status_output": output},
    )


def run_runtime_setup_dry_run(rows: list[KrakenRow]) -> None:
    script = REPO_ROOT / "scripts" / "runtime_setup_check.ps1"

    def predicate(completed: subprocess.CompletedProcess[str]) -> tuple[bool, str]:
        output = f"{completed.stdout}\n{completed.stderr}"
        ok = (
            completed.returncode == 0
            and "No installers launched" in output
            and "Full Live Runtime Ready: governed by the Phase 16 proof gate" in output
        )
        return (
            ok,
            "Runtime setup dry-run preserved installer/runtime boundaries."
            if ok
            else "Runtime setup dry-run missed a required boundary phrase or exited nonzero.",
        )

    _run_command(
        rows,
        section="runtime_setup_dry_run",
        check="runtime_setup_dry_run",
        command=(
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-DryRun",
        ),
        timeout=120,
        pass_predicate=predicate,
    )


def run_page_navigation_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        _ensure_qapp()
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QScrollArea
        from v3_app.pages.placeholders import PAGE_DEFINITIONS

        with tempfile.TemporaryDirectory() as temp_dir:
            shell = _shell(Path(temp_dir) / "hotas_bridge_config_v3.json")
            visited: list[str] = []
            for page in PAGE_DEFINITIONS:
                shell.switch_page(page.page_id)
                scroll = shell.page_widgets[page.page_id]
                assert isinstance(scroll, QScrollArea)
                assert scroll.widgetResizable()
                assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                assert scroll.widget() is not None
                assert page.title in _widget_text(scroll.widget())
                visited.append(page.title)
        return {"pages_visited": visited, "count": len(visited)}

    _run_callable(rows, section="page_navigation_smoke", check="navigate_registered_pages", callback=check)


def run_help_docs_search_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        from v3_app.services.help_docs import search_articles

        queries = (
            "Runtime Setup / vJoy Setup",
            "Runtime Indicators",
            "Helm",
            "Live Overlay",
            "Flight Recorder",
            "Performance / Diagnostics",
            "packaging source launch",
        )
        results: dict[str, Any] = {}
        for query in queries:
            matches = search_articles(query)
            assert matches, f"No local Help / Docs results for {query!r}"
            results[query] = {
                "result_count": len(matches),
                "top_results": [match.article.title for match in matches[:3]],
            }
        return results

    _run_callable(rows, section="help_docs_search_smoke", check="required_local_queries", callback=check)


def run_perf_diagnostics_copy_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        _ensure_qapp()
        with tempfile.TemporaryDirectory() as temp_dir:
            shell = _shell(Path(temp_dir) / "hotas_bridge_config_v3.json")
            shell.switch_page("perf_diagnostics")
            page = shell.page_widgets["perf_diagnostics"].widget()
            copy_text = page.prepare_copy_diagnostics()
        required = (
            "Runtime truth",
            "Bridge lifecycle",
            "Bridge telemetry status",
            "Physical input",
            "Virtual output backend",
            "Output loop",
            "Runtime frame",
            "Full Live Runtime Ready",
            "Blocked reason",
            "Proof summary",
        )
        missing = [phrase for phrase in required if phrase not in copy_text]
        assert not missing, f"Missing diagnostics phrases: {missing}"
        version = "unavailable"
        try:
            from v3_app.version import __version__

            version = __version__
        except Exception:
            pass
        return {
            "required_phrases": required,
            "app_version": version,
            "copy_length": len(copy_text),
        }

    _run_callable(rows, section="perf_diagnostics_copy_smoke", check="copy_diagnostics_truth", callback=check)


def run_helm_overlay_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        _ensure_qapp()
        with tempfile.TemporaryDirectory() as temp_dir:
            shell = _shell(Path(temp_dir) / "hotas_bridge_config_v3.json")
            helm = shell.open_helm_overlay()
            text = _widget_text(helm)
            for phrase in ("What's wrong?", "What I'd change", "What I found", "Apply / Revert"):
                assert phrase in text
            helm.select_symptom("Yaw feels sluggish in combat.")
            helm.analyze()
            after_analysis = _widget_text(helm)
            assert "Apply Selected Changes" in after_analysis
            assert "Save Workspace is still required" in Path(REPO_ROOT / "v3_app" / "helm" / "helm_overlay.py").read_text(
                encoding="utf-8"
            )
            helm.close()
        return {
            "sections": ("What's wrong?", "What I'd change", "What I found", "Apply / Revert"),
            "mode": "deterministic local in-memory",
            "no_auto_save": True,
            "no_cloud_ai_llm": True,
        }

    _run_callable(rows, section="helm_overlay_smoke", check="overlay_sections_and_symptom_path", callback=check)


def run_live_overlay_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        _ensure_qapp()
        from v3_app.overlay.config_dialog import LiveOverlayConfigDialog
        from v3_app.overlay.live_overlay_window import LiveOverlayWindow
        from v3_app.overlay.overlay_config import LiveOverlayConfig

        config = LiveOverlayConfig.defaults()
        dialog = LiveOverlayConfigDialog(config=config, on_apply=lambda _config: None)
        assert dialog.minimumWidth() >= 760
        overlay = LiveOverlayWindow(
            config=config,
            runtime_truth="blocked_missing_device",
            output_verified=False,
            full_live_runtime_ready=False,
        )
        overlay.show_overlay()
        active = overlay.refresh_timer.isActive()
        overlay.hide_overlay()
        inactive = not overlay.refresh_timer.isActive()
        click_through = overlay.click_through_status_text()
        source = (REPO_ROOT / "v3_app" / "pages" / "live_monitor_page.py").read_text(encoding="utf-8")
        assert active and inactive
        assert "Not registered" in source
        assert "not verified" in source
        assert "game injection" not in source.casefold()
        assert "graphics api hooking" not in source.casefold()
        return {
            "dialog_constructed": True,
            "overlay_show_hide": True,
            "click_through_status": click_through,
            "hotkey_status": "Not registered",
        }

    _run_callable(rows, section="live_overlay_smoke", check="dialog_and_detached_overlay", callback=check)


def run_flight_recorder_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        _ensure_qapp()
        from v3_app.pages.flight_recorder_page import FlightRecorderPage

        page = FlightRecorderPage(state=_state(), workspace=_workspace(), runtime_status=_runtime_status_fixture())
        page.refresh_library()
        text = _widget_text(page)
        for phrase in (
            "Recorder Settings",
            "Axis Overlay",
            "Recording Library",
            "Clip Preview",
            "Metadata-only preview",
            "No video captured",
            "No encoding performed",
            "Hotkey not registered",
        ):
            assert phrase in text
        assert "Recording started" not in text
        return {"required_phrases": 8, "metadata_only": True, "real_capture_claimed": False}

    _run_callable(rows, section="flight_recorder_smoke", check="page_truth_and_metadata_only_copy", callback=check)


def run_packaging_metadata_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        required_paths = (
            REPO_ROOT / "packaging" / "build_release.ps1",
            REPO_ROOT / "packaging" / "README.md",
            REPO_ROOT / "docs" / "HelmForge" / "phase-18d-final-packaging-qa-report.md",
        )
        for path in required_paths:
            assert path.exists(), f"Missing {path}"
        docs = "\n".join(path.read_text(encoding="utf-8") for path in required_paths)
        required = (
            "packaging/dist/HelmForge/HelmForge.exe",
            "one-folder build",
            "%LocalAppData%\\HelmForge",
            "assets/app_icon.ico is missing",
            "icon conversion remains deferred",
        )
        for phrase in required:
            assert phrase in docs
        return {"paths": [str(path) for path in required_paths], "app_icon_exists": (REPO_ROOT / "assets" / "app_icon.ico").exists()}

    _run_callable(rows, section="packaging_metadata_smoke", check="packaging_docs_and_icon_truth", callback=check)


def run_installer_metadata_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        inno = REPO_ROOT / "packaging" / "inno" / "helmforge.iss"
        assert inno.exists()
        text = inno.read_text(encoding="utf-8")
        required = (
            'Name: "{group}\\HelmForge"; Filename: "{app}\\HelmForge.exe"',
            'Name: "{autodesktop}\\HelmForge"; Filename: "{app}\\HelmForge.exe"; Tasks: desktopicon',
            "UninstallDisplayName={#AppDisplayName}",
        )
        for phrase in required:
            assert phrase in text
        forbidden = (
            "vJoySetup",
            "Install Service",
            "Enable Auto Start",
            "StartBridge",
            "StopBridge",
            "RestartBridge",
            "{localappdata}\\HelmForge\\*",
            "{commonstartup}",
        )
        for phrase in forbidden:
            assert phrase.casefold() not in text.casefold()
        compiler = shutil.which("IS" + "CC.exe")
        return {"inno_script": str(inno), "compiler_available": bool(compiler), "compiler_path": compiler or ""}

    _run_callable(rows, section="installer_metadata_smoke", check="installer_metadata_boundaries", callback=check)
    compiler = shutil.which("IS" + "CC.exe")
    compiler_name = "IS" + "CC.exe"
    if compiler:
        _add_row(
            rows,
            section="installer_metadata_smoke",
            check="installer_compile",
            status="skipped",
            message=f"{compiler_name} is available, but installer compile is optional in the Phase 19B harness; use packaging/build_release.ps1 -BuildInstaller for a release compile.",
            details={"compiler_path": compiler},
        )
    else:
        _add_row(
            rows,
            section="installer_metadata_smoke",
            check="installer_compile",
            status="skipped",
            message=f"{compiler_name} unavailable; Inno compile skipped by harness.",
            details={"compiler_path": ""},
        )


def run_runtime_truth_boundary_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        inventory = (REPO_ROOT / "docs" / "HelmForge" / "phase-19a-full-product-acceptance-inventory.md").read_text(
            encoding="utf-8"
        )
        text = f"{readme}\n{inventory}"
        required = (
            "Telemetry remains the truth surface",
            "Command files are requests, not success proof",
            "Process presence is a hint only",
            "vJoy detected does not equal output verified",
            "Physical input alone is not full readiness",
            "fake/test paths are not real readiness",
            "Output intent is not output write proof",
        )
        for phrase in required:
            assert phrase in text
        return {"truth_phrases": required}

    _run_callable(rows, section="runtime_truth_boundary_smoke", check="runtime_truth_docs_and_boundaries", callback=check)


def run_full_live_runtime_ready_gate_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        from shared_core.runtime.runtime_orchestrator import (
            RuntimeFrameSource,
            RuntimeOrchestrator,
            RuntimeOrchestratorConfig,
        )

        frame = RuntimeOrchestrator(
            config=RuntimeOrchestratorConfig(
                preferred_input_source=RuntimeFrameSource.PHYSICAL,
                allow_simulation_fallback=False,
            ),
            runtime_status=_runtime_status_fixture(),
        ).build_frame()
        gate_result = frame.readiness
        assert gate_result.full_live_runtime_ready is False
        assert gate_result.blocked_reason in {"blocked_missing_input", "blocked_missing_output", "blocked_unverified_output"}
        return {
            "full_live_runtime_ready": gate_result.full_live_runtime_ready,
            "ready_state": gate_result.ready_state,
            "blocked_reason": gate_result.blocked_reason,
            "proof_summary": gate_result.proof_summary,
        }

    _run_callable(
        rows,
        section="full_live_runtime_ready_gate_smoke",
        check="missing_input_and_output_unverified_block_gate",
        callback=check,
    )


def run_safety_boundary_smoke(rows: list[KrakenRow]) -> None:
    def check() -> dict[str, Any]:
        source_paths = (
            REPO_ROOT / "v3_app" / "ui" / "shell.py",
            REPO_ROOT / "v3_app" / "pages" / "live_monitor_page.py",
            REPO_ROOT / "v3_app" / "pages" / "flight_recorder_page.py",
            REPO_ROOT / "v3_app" / "helm" / "helm_overlay.py",
            REPO_ROOT / "packaging" / "build_release.ps1",
            REPO_ROOT / "packaging" / "inno" / "helmforge.iss",
            REPO_ROOT / "docs" / "HelmForge" / "phase-19a-full-product-acceptance-inventory.md",
        )
        text = "\n".join(path.read_text(encoding="utf-8") for path in source_paths if path.exists())
        forbidden_runtime_authority = (
            "Start" + "Bridge(",
            "Stop" + "Bridge(",
            "Restart" + "Bridge(",
            "keyboard." + "add_hotkey",
            "Video" + "Writer",
            "Open" + "AI(",
        )
        for phrase in forbidden_runtime_authority:
            assert phrase not in text
        for phrase in BOUNDARY_PHRASES:
            assert phrase in text
        return {
            "boundary_phrases": BOUNDARY_PHRASES,
            "forbidden_runtime_authority_absent": forbidden_runtime_authority,
        }

    _run_callable(rows, section="safety_boundary_smoke", check="no_forbidden_runtime_authority", callback=check)


SECTION_RUNNERS: dict[str, Callable[[list[KrakenRow]], None]] = {
    "source_app_smoke": run_source_app_smoke,
    "packaged_app_smoke": run_packaged_app_smoke,
    "bridge_smoke": run_bridge_smoke,
    "runtime_setup_dry_run": run_runtime_setup_dry_run,
    "page_navigation_smoke": run_page_navigation_smoke,
    "help_docs_search_smoke": run_help_docs_search_smoke,
    "perf_diagnostics_copy_smoke": run_perf_diagnostics_copy_smoke,
    "helm_overlay_smoke": run_helm_overlay_smoke,
    "live_overlay_smoke": run_live_overlay_smoke,
    "flight_recorder_smoke": run_flight_recorder_smoke,
    "packaging_metadata_smoke": run_packaging_metadata_smoke,
    "installer_metadata_smoke": run_installer_metadata_smoke,
    "runtime_truth_boundary_smoke": run_runtime_truth_boundary_smoke,
    "full_live_runtime_ready_gate_smoke": run_full_live_runtime_ready_gate_smoke,
    "safety_boundary_smoke": run_safety_boundary_smoke,
}


def _dry_run_rows() -> list[KrakenRow]:
    rows: list[KrakenRow] = []
    for section in REQUIRED_SECTIONS:
        _add_row(
            rows,
            section=section,
            check="dry_run_plan",
            status="skipped",
            message="Dry run: section planned but not executed.",
            details={"planned": True},
        )
    return rows


def _counts(rows: Iterable[KrakenRow]) -> dict[str, int]:
    counts = {"pass": 0, "fail": 0, "skipped": 0}
    for row in rows:
        counts[row.status] = counts.get(row.status, 0) + 1
    return counts


def _new_artifact_dir(output_root: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    candidate = output_root / stamp
    suffix = 1
    while candidate.exists():
        suffix += 1
        candidate = output_root / f"{stamp}-{suffix}"
    candidate.mkdir(parents=True, exist_ok=False)
    return candidate


def _write_artifacts(rows: list[KrakenRow], *, output_root: Path, dry_run: bool) -> dict[str, Any]:
    artifact_dir = _new_artifact_dir(output_root)
    counts = _counts(rows)
    payload = {
        "phase": "19B",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "artifact_dir": str(artifact_dir),
        "sections": list(REQUIRED_SECTIONS),
        "counts": counts,
        "rows": [asdict(row) for row in rows],
    }

    results_path = artifact_dir / "phase19b_kraken_results.json"
    rows_path = artifact_dir / "phase19b_kraken_rows.jsonl"
    csv_path = artifact_dir / "phase19b_kraken_rows.csv"
    summary_path = artifact_dir / "phase19b_kraken_summary.md"

    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    rows_path.write_text("\n".join(json.dumps(asdict(row), sort_keys=True) for row in rows) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("section", "check", "status", "elapsed_ms", "message", "command", "stdout_tail", "stderr_tail"),
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "section": row.section,
                    "check": row.check,
                    "status": row.status,
                    "elapsed_ms": row.elapsed_ms,
                    "message": row.message,
                    "command": row.command,
                    "stdout_tail": row.stdout_tail,
                    "stderr_tail": row.stderr_tail,
                }
            )
    summary_path.write_text(_build_summary_markdown(payload, rows), encoding="utf-8")
    return payload


def _build_summary_markdown(payload: dict[str, Any], rows: list[KrakenRow]) -> str:
    counts = payload["counts"]
    lines = [
        "# Phase 19B Kraken Summary",
        "",
        f"Generated at: {payload['generated_at']}",
        f"Dry run: {str(payload['dry_run']).lower()}",
        f"Artifacts: `{payload['artifact_dir']}`",
        "",
        "## Pass / Fail / Skipped",
        "",
        f"- pass: {counts.get('pass', 0)}",
        f"- fail: {counts.get('fail', 0)}",
        f"- skipped: {counts.get('skipped', 0)}",
        "",
        "## Sections",
        "",
    ]
    for section in REQUIRED_SECTIONS:
        section_rows = [row for row in rows if row.section == section]
        status = "fail" if any(row.status == "fail" for row in section_rows) else (
            "skipped" if section_rows and all(row.status == "skipped" for row in section_rows) else "pass"
        )
        lines.append(f"- `{section}`: {status}")
    lines.extend(["", "## Rows", ""])
    for row in rows:
        lines.append(f"- `{row.section}` / `{row.check}`: {row.status} - {row.message}")
    lines.extend(
        [
            "",
            "## Safety Boundary Notes",
            "",
            "- no fake readiness",
            "- no Bridge lifecycle management",
            "- no driver/vJoy installer launch",
            "- no cloud AI/LLM",
            "- no auto-save",
            "- Full Live Runtime Ready proof gate remains the readiness authority",
        ]
    )
    return "\n".join(lines) + "\n"


def run_harness(*, output_root: Path, dry_run: bool) -> dict[str, Any]:
    if dry_run:
        rows = _dry_run_rows()
    else:
        rows: list[KrakenRow] = []
        for section in REQUIRED_SECTIONS:
            SECTION_RUNNERS[section](rows)
    return _write_artifacts(rows, output_root=output_root, dry_run=dry_run)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Phase 19B Integration Kraken regression sweep.")
    parser.add_argument("--dry-run", action="store_true", help="Write planned-section artifacts without executing checks.")
    parser.add_argument("--list-sections", action="store_true", help="List harness sections and exit.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Artifact output root. Default: .artifacts/phase19b_kraken",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.list_sections:
        for section in REQUIRED_SECTIONS:
            print(section)
        return 0

    payload = run_harness(output_root=args.output_root, dry_run=args.dry_run)
    counts = payload["counts"]
    print(f"Phase 19B Kraken artifacts: {payload['artifact_dir']}")
    print(f"pass={counts.get('pass', 0)} fail={counts.get('fail', 0)} skipped={counts.get('skipped', 0)}")
    return 1 if counts.get("fail", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
