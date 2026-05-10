from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from bridge_app.service import BridgeService, BridgeServiceOptions
from shared_core.runtime.telemetry import BridgeTelemetrySnapshot
from v3_app.services.embedded_bridge_telemetry import record_embedded_bridge_telemetry
from v3_app.services.live_refresh import LIVE_REFRESH_INTERVAL_MS


BridgeServiceFactory = Callable[[], BridgeService]
TelemetryCallback = Callable[[BridgeTelemetrySnapshot], None]


class EmbeddedBridgeRuntime(QObject):
    def __init__(
        self,
        *,
        on_telemetry: TelemetryCallback,
        service_factory: BridgeServiceFactory | None = None,
        interval_ms: int = LIVE_REFRESH_INTERVAL_MS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_telemetry = on_telemetry
        self._threaded = service_factory is None
        self._service = None if self._threaded else service_factory()
        self._timer: QTimer | None = None
        self._thread: QThread | None = None
        self._worker: _BridgeTickWorker | None = None
        if self._threaded:
            self._thread = QThread(self)
            self._worker = _BridgeTickWorker(
                service_factory=lambda: BridgeService(
                    BridgeServiceOptions(
                        simulate=False,
                        enable_live_input=True,
                        enable_output_verification=True,
                        enable_output_loop=True,
                        tick_interval_ms=interval_ms,
                    )
                ),
                interval_ms=interval_ms,
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
        record_embedded_bridge_telemetry(telemetry)
        self._on_telemetry(telemetry)
        return telemetry


class _BridgeTickWorker(QObject):
    telemetry_ready = Signal(object)

    def __init__(self, *, service_factory: BridgeServiceFactory, interval_ms: int) -> None:
        super().__init__()
        self._service_factory = service_factory
        self._interval_ms = interval_ms
        self._service: BridgeService | None = None
        self._timer: QTimer | None = None

    @Slot()
    def start(self) -> None:
        self._service = self._service_factory()
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self.tick)
        self.tick()
        self._timer.start()

    @Slot()
    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()

    @Slot()
    def tick(self) -> None:
        if self._service is None:
            return
        telemetry = self._service.run_once()
        record_embedded_bridge_telemetry(telemetry)
        self.telemetry_ready.emit(telemetry)
