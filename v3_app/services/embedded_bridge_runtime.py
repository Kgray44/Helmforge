from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Mapping

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from bridge_app.ipc import write_telemetry
from bridge_app.service import BridgeService, BridgeServiceOptions
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.services.embedded_bridge_telemetry import record_embedded_bridge_telemetry
from v3_app.services.live_refresh import LIVE_REFRESH_INTERVAL_MS


BridgeServiceFactory = Callable[[], BridgeService]
TelemetryCallback = Callable[[BridgeTelemetrySnapshot], None]
JsonTelemetryWriter = Callable[[Path, Mapping[str, object]], object]


class AsyncTelemetryJsonPublisher:
    def __init__(self, *, writer: JsonTelemetryWriter = write_telemetry) -> None:
        self._writer = writer
        self._lock = threading.RLock()
        self._event = threading.Event()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest: tuple[Path, dict[str, object]] | None = None
        self._status: dict[str, object] = {
            "enabled": True,
            "pending": False,
            "write_count": 0,
            "failure_count": 0,
            "last_status": "idle",
            "last_error": "",
            "last_duration_ms": None,
        }

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="helmforge-embedded-json-publisher", daemon=True)
        self._thread.start()

    def submit(self, path: Path, payload: Mapping[str, object]) -> None:
        with self._lock:
            self._latest = (Path(path), dict(payload))
            self._status["pending"] = True
        self._event.set()

    def stop(self, *, timeout_ms: int = 1000) -> None:
        self._stop_event.set()
        self._event.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(max(0.0, timeout_ms / 1000.0))

    def status(self) -> dict[str, object]:
        with self._lock:
            return dict(self._status)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._event.wait(0.1)
            if self._stop_event.is_set():
                break
            with self._lock:
                item = self._latest
                self._latest = None
                self._status["pending"] = False
                self._event.clear()
            if item is None:
                continue
            path, payload = item
            started = time.perf_counter()
            try:
                self._writer(path, payload)
            except (PermissionError, OSError) as exc:
                duration_ms = (time.perf_counter() - started) * 1000.0
                with self._lock:
                    self._status.update(
                        {
                            "failure_count": int(self._status["failure_count"]) + 1,
                            "last_status": "error",
                            "last_error": str(exc),
                            "last_duration_ms": duration_ms,
                        }
                    )
            else:
                duration_ms = (time.perf_counter() - started) * 1000.0
                with self._lock:
                    self._status.update(
                        {
                            "write_count": int(self._status["write_count"]) + 1,
                            "last_status": "ok",
                            "last_error": "",
                            "last_duration_ms": duration_ms,
                        }
                    )


class EmbeddedBridgeRuntime(QObject):
    def __init__(
        self,
        *,
        on_telemetry: TelemetryCallback,
        service_factory: BridgeServiceFactory | None = None,
        interval_ms: int = LIVE_REFRESH_INTERVAL_MS,
        threaded: bool | None = None,
        publish_diagnostic_json: bool = True,
        diagnostic_json_rate_hz: float = 5.0,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_telemetry = on_telemetry
        self._threaded = service_factory is None if threaded is None else bool(threaded)
        active_service_factory = service_factory or _default_bridge_service_factory(interval_ms)
        self._service = None if self._threaded else active_service_factory()
        self._timer: QTimer | None = None
        self._thread: QThread | None = None
        self._worker: _BridgeTickWorker | None = None
        if self._threaded:
            self._thread = QThread(self)
            self._worker = _BridgeTickWorker(
                service_factory=active_service_factory,
                interval_ms=interval_ms,
                publish_diagnostic_json=publish_diagnostic_json,
                diagnostic_json_rate_hz=diagnostic_json_rate_hz,
            )
            self._worker.moveToThread(self._thread)
            self._thread.started.connect(self._worker.start)
            self._worker.telemetry_ready.connect(self._on_telemetry)
        else:
            self._timer = QTimer(self)
            self._timer.setInterval(interval_ms)
            self._timer.timeout.connect(self.tick)

    @property
    def service(self) -> BridgeService:
        if self._service is None:
            raise RuntimeError("Embedded bridge service lives on the worker thread.")
        return self._service

    def start(self) -> None:
        if self._threaded:
            if self._thread is not None and not self._thread.isRunning():
                self._thread.start()
            return
        self.tick()
        if self._timer is not None:
            self._timer.start()

    def stop(self) -> None:
        if self._threaded:
            if self._worker is not None:
                self._worker.stop()
            if self._thread is not None and self._thread.isRunning():
                self._thread.quit()
                self._thread.wait(2000)
            return
        if self._timer is not None:
            self._timer.stop()

    def tick(self) -> BridgeTelemetrySnapshot:
        if self._service is None:
            raise RuntimeError("Synchronous ticks are unavailable for threaded embedded bridge runtime.")
        telemetry = self._service.run_once()
        payload = self._service.build_telemetry_payload(telemetry)
        record_embedded_bridge_telemetry(telemetry, payload=payload)
        self._on_telemetry(telemetry)
        return telemetry


class _BridgeTickWorker(QObject):
    telemetry_ready = Signal(object)

    def __init__(
        self,
        *,
        service_factory: BridgeServiceFactory,
        interval_ms: int,
        publish_diagnostic_json: bool = True,
        diagnostic_json_rate_hz: float = 5.0,
    ) -> None:
        super().__init__()
        self._service_factory = service_factory
        self._interval_ms = interval_ms
        self._publish_diagnostic_json = publish_diagnostic_json
        self._service: BridgeService | None = None
        self._timer: QTimer | None = None
        self._json_publisher = AsyncTelemetryJsonPublisher() if publish_diagnostic_json else None
        self._diagnostic_json_interval_seconds = 1.0 / max(0.001, float(diagnostic_json_rate_hz))
        self._last_diagnostic_json_publish_at: float | None = None

    @Slot()
    def start(self) -> None:
        self._service = self._service_factory()
        if self._json_publisher is not None:
            self._json_publisher.start()
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self.tick)
        self.tick()
        self._timer.start()

    @Slot()
    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        if self._json_publisher is not None:
            self._json_publisher.stop()

    @Slot()
    def tick(self) -> None:
        if self._service is None:
            return
        started = time.perf_counter()
        telemetry = self._service.run_once(publish_telemetry=False)
        duration_ms = (time.perf_counter() - started) * 1000.0
        timing = getattr(self._service, "timing", None)
        if timing is not None:
            timing.last_worker_tick_duration_ms = duration_ms
            if duration_ms > max(1, self._interval_ms) * 1.5:
                timing.embedded_worker_late_tick_count = int(getattr(timing, "embedded_worker_late_tick_count", 0)) + 1
        payload = self._service.build_telemetry_payload(telemetry)
        record_embedded_bridge_telemetry(telemetry, payload=payload)
        self.telemetry_ready.emit(telemetry)
        now = time.monotonic()
        publish_json = (
            self._json_publisher is not None
            and (
                self._last_diagnostic_json_publish_at is None
                or now - self._last_diagnostic_json_publish_at >= self._diagnostic_json_interval_seconds
            )
        )
        if publish_json and self._json_publisher is not None:
            try:
                self._json_publisher.submit(self._service.options.telemetry_path, payload)
                self._last_diagnostic_json_publish_at = now
            except Exception:
                pass


def _default_bridge_service_factory(interval_ms: int) -> BridgeServiceFactory:
    return lambda: BridgeService(
        BridgeServiceOptions(
            simulate=False,
            enable_live_input=True,
            enable_output_verification=True,
            enable_output_loop=True,
            tick_interval_ms=interval_ms,
            enable_periodic_discovery_refresh=False,
            enable_telemetry_stream=False,
        )
    )
