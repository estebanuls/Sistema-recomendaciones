"""Administrative endpoints for model retraining."""

from __future__ import annotations

from backend.app.api import ApiError

def retrain(*, context, current_user, **_):
    if not current_user.is_admin:
        raise ApiError(403, "Se requiere rol de administrador.")
    if context.training_supervisor is not None:
        report = context.training_supervisor.force_retrain()
    else:
        from backend.ml.entrenamiento import ensure_pipeline_outputs

        report = ensure_pipeline_outputs(context.settings, force=True)
        context.recommendation_service.refresh_model()
    return 200, {
        "detail": "Reentrenamiento completado.",
        "report": report,
    }
