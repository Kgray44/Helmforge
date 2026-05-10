from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from shared_core.runtime.hotas_input import WindowsRawInputBackend, build_physical_input_fidelity


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp() -> str:
    return _now().strftime("%Y%m%dT%H%M%SZ")


def _snapshot_axes(snapshot) -> dict[str, float]:
    return {
        axis.logical_name or axis.raw_name: axis.normalized_value
        for axis in snapshot.axes
    }


def _snapshot_buttons(snapshot) -> dict[str, bool]:
    return {f"B{button.button_index}": button.pressed for button in snapshot.buttons}


def _snapshot_hats(snapshot) -> dict[str, str]:
    return {f"Hat {hat.hat_index}": hat.normalized_direction for hat in snapshot.hats}


def run_probe(duration_ms: int, output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    frame_path = output / "frames.jsonl"
    summary_path = output / "summary.json"
    markdown_path = output / "summary.md"

    backend = WindowsRawInputBackend()
    devices = backend.enumerate_devices()
    selected = next((device for device in devices if device.is_supported), devices[0] if devices else None)
    status = None
    if selected is not None:
        status = backend.open_device(selected.device_id)

    deadline = time.monotonic() + max(0, duration_ms) / 1000.0
    frame_count = 0
    active_count = 0
    axis_changes: dict[str, dict[str, float]] = {}
    button_seen: set[str] = set()
    hat_seen: set[str] = set()
    warnings: list[str] = []
    errors: list[str] = []

    with frame_path.open("w", encoding="utf-8") as handle:
        while time.monotonic() < deadline:
            snapshot = backend.read_current_state()
            fidelity = build_physical_input_fidelity(snapshot, backend=backend, sampled_at=_now())
            payload = {
                "captured_at": _now().isoformat(),
                "sequence": snapshot.sequence,
                "sampling_active": snapshot.sampling_active,
                "sampling_status": snapshot.sampling_status.value,
                "sample_age_ms": fidelity.sample_age_ms,
                "estimated_sample_rate_hz": fidelity.estimated_sample_rate_hz,
                "axes": _snapshot_axes(snapshot),
                "buttons": _snapshot_buttons(snapshot),
                "hats": _snapshot_hats(snapshot),
                "warnings": list(snapshot.warnings),
                "errors": list(snapshot.errors),
            }
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
            frame_count += 1
            if snapshot.sampling_active:
                active_count += 1
            for name, value in payload["axes"].items():
                bucket = axis_changes.setdefault(name, {"min": value, "max": value})
                bucket["min"] = min(bucket["min"], value)
                bucket["max"] = max(bucket["max"], value)
            button_seen.update(name for name, pressed in payload["buttons"].items() if pressed)
            hat_seen.update(direction for direction in payload["hats"].values() if direction)
            warnings.extend(payload["warnings"])
            errors.extend(payload["errors"])
            time.sleep(0.02)

    backend.close_device()
    summary = {
        "mode": "raw_input_probe",
        "started_at": _now().isoformat(),
        "duration_ms": duration_ms,
        "backend_name": backend.get_capabilities().backend_name,
        "backend_kind": backend.get_capabilities().backend_kind,
        "devices": [
            {
                "device_id": device.device_id,
                "display_name": device.display_name,
                "vendor_id": device.vendor_id,
                "product_id": device.product_id,
                "is_supported": device.is_supported,
                "support_reason": device.support_reason,
            }
            for device in devices
        ],
        "selected_device_id": selected.device_id if selected else None,
        "open_status": status.status if status else "no_device",
        "open_message": status.message if status else "No Raw Input device was discovered.",
        "frame_count": frame_count,
        "active_sample_count": active_count,
        "axis_ranges": axis_changes,
        "buttons_pressed_seen": sorted(button_seen),
        "hat_directions_seen": sorted(hat_seen),
        "warnings": sorted(set(warnings)),
        "errors": sorted(set(errors)),
        "artifact_paths": {
            "summary_json": str(summary_path),
            "summary_md": str(markdown_path),
            "frames_jsonl": str(frame_path),
        },
        "runtime_truth_note": "Raw Input probe is physical-input-only and does not prove vJoy output writes or Full Live Runtime Ready.",
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(_markdown_summary(summary), encoding="utf-8")
    return summary


def _markdown_summary(summary: dict[str, object]) -> str:
    return "\n".join(
        [
            "# HF-LRDC-6A Raw Input Probe",
            "",
            f"- Backend: `{summary['backend_name']}` / `{summary['backend_kind']}`",
            f"- Selected device: `{summary['selected_device_id']}`",
            f"- Open status: `{summary['open_status']}`",
            f"- Frames captured: `{summary['frame_count']}`",
            f"- Active samples: `{summary['active_sample_count']}`",
            f"- Buttons pressed seen: `{', '.join(summary['buttons_pressed_seen']) or 'none'}`",
            f"- Hat directions seen: `{', '.join(summary['hat_directions_seen']) or 'none'}`",
            "",
            "Raw Input probe is physical-input-only. It does not prove vJoy output writes or Full Live Runtime Ready.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe HelmForge Windows Raw Input HOTAS sampling.")
    parser.add_argument("--duration-ms", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=Path(".artifacts/hf-lrdc/raw-input-probe") / _timestamp())
    args = parser.parse_args()
    summary = run_probe(args.duration_ms, args.output)
    print(f"Raw Input probe artifacts: {args.output}")
    print(f"backend={summary['backend_name']} selected={summary['selected_device_id']} active_samples={summary['active_sample_count']}")
    if summary["errors"]:
        print("errors=" + "; ".join(summary["errors"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
