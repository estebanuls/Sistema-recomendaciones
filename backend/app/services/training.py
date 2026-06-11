"""Background orchestration for automatic retraining."""

from __future__ import annotations

from threading import Event, Lock, Thread

from backend.ml.entrenamiento import ensure_pipeline_outputs, is_training_required


class TrainingSupervisor:
    def __init__(self, *, settings, recommendation_service, logger):
        self.settings = settings
        self.recommendation_service = recommendation_service
        self.logger = logger
        self.interval_seconds = max(0, int(settings.auto_retrain_interval_seconds))
        self._stop_event = Event()
        self._lock = Lock()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self.interval_seconds <= 0:
            self.logger.info("Supervision de reentrenamiento automatico deshabilitada.")
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run_loop, name="training-supervisor", daemon=True)
        self._thread.start()
        self.logger.info(
            "Supervision de reentrenamiento automatica activa cada %s segundos.",
            self.interval_seconds,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def force_retrain(self) -> dict[str, object]:
        return self._run_training(force=True, reason="Reentrenamiento manual solicitado.")

    def poll_once(self) -> bool:
        if self._lock.locked():
            return False
        if not is_training_required(self.settings):
            return False
        self._run_training(
            force=False,
            reason="Se detectaron cambios en el dataset; iniciando reentrenamiento automatico.",
        )
        return True

    def _run_loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            try:
                self.poll_once()
            except Exception as exc:  # pragma: no cover - logging path
                self.logger.error("Fallo el reentrenamiento automatico: %s", exc, exc_info=True)

    def _run_training(self, *, force: bool, reason: str) -> dict[str, object]:
        with self._lock:
            self.logger.info(reason)
            report = ensure_pipeline_outputs(self.settings, force=force)
            self.recommendation_service.refresh_model()
            self.logger.info(
                "Reentrenamiento completado. Factores latentes: %s.",
                report.get("latent_factors", self.settings.latent_factors),
            )
            return report
