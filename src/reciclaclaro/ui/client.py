"""UI boundary: typed mock fixtures or delegation to the shared orchestrator.

RECICLACLARO_UI_MODE: mock (default) or live.
RECICLACLARO_UI_SCENARIO: clear_photo (default), ambiguous_material,
not_admitted, api_error. This only selects mock identification responses;
comparison uses canned material examples, never the real center rule engine.

Only IdentificationResult supports is_mock. Mock centers have MOCK in their
name and comparison reasons are explicitly labelled. No schema is extended.
The UI owns invalidation on a new photo; compare receives no image argument.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from reciclaclaro.contracts import (
    AnalysisRequest, AppError, Center, ComparisonResult, ConfirmedItem,
    DeliveryPlan, IdentificationResult, ReciclaClaroError,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_SCENARIOS = frozenset({"clear_photo", "ambiguous_material", "not_admitted", "api_error"})
_Model = TypeVar("_Model", bound=BaseModel)


def _error(category: str, message: str) -> ReciclaClaroError:
    return ReciclaClaroError(AppError(category=category, message=message, retryable=False))


def _mode() -> str:
    mode = os.environ.get("RECICLACLARO_UI_MODE", "mock").strip().lower()
    if mode not in {"mock", "live"}:
        raise _error("entrada_invalida", "RECICLACLARO_UI_MODE debe ser mock o live.")
    return mode


def _read(filename: str):
    try:
        return json.loads((_FIXTURES / filename).read_text(encoding="utf-8"))
    except OSError as exc:
        raise _error("sin_datos", f"No se puede leer el ejemplo MOCK {filename}.") from exc
    except (ValueError, UnicodeError) as exc:
        raise _error("formato_invalido", f"El ejemplo MOCK {filename} no es JSON válido.") from exc


def _validate(model: type[_Model], data) -> _Model:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise _error("formato_invalido", f"La respuesta no cumple el contrato {model.__name__}.") from exc


def _orchestrator():
    # Lazy import: mock mode needs neither backend code nor provider packages.
    try:
        return importlib.import_module("reciclaclaro.orchestrator")
    except ImportError as exc:
        raise _error(
            "sin_datos",
            "No se pudo cargar reciclaclaro.orchestrator en modo live. "
            "Verifica la instalación del orquestador y sus dependencias.",
        ) from exc


def identify(req: AnalysisRequest) -> IdentificationResult:
    """Identify via the orchestrator or replay a selected, explicitly mock example."""
    if _mode() == "live":
        return _validate(IdentificationResult, _orchestrator().identify(req))
    scenario = os.environ.get("RECICLACLARO_UI_SCENARIO", "clear_photo")
    if scenario not in _SCENARIOS:
        raise _error("entrada_invalida", "Escenario MOCK desconocido.")
    data = _read(f"{scenario}.json")
    if scenario == "api_error":
        raise ReciclaClaroError(_validate(AppError, data))
    result = _validate(IdentificationResult, data)
    return result.model_copy(update={"is_mock": True, "backend": req.backend})


def list_centers() -> list[Center]:
    """Return typed centers; fixture destinations are fictional and labelled MOCK."""
    data = _orchestrator().list_centers() if _mode() == "live" else _read("centers.json")
    if not isinstance(data, list):
        raise _error("formato_invalido", "La lista de centros debe ser una lista.")
    return [_validate(Center, center) for center in data]


def compare(items: list[ConfirmedItem], center_id: str) -> DeliveryPlan:
    """Delegate live comparison; in mock, bind canned examples to confirmed IDs.

    Fixture templates describe demo outcomes, not recycling advice. Unrepresented
    materials use the pending example. No catalog rules are evaluated here.
    """
    if _mode() == "live":
        return _validate(DeliveryPlan, _orchestrator().compare(items, center_id))
    if not items or len({item.item_id for item in items}) != len(items):
        raise _error("entrada_invalida", "Confirma objetos con identificadores únicos antes de comparar.")
    center = next((c for c in list_centers() if c.center_id == center_id), None)
    if center is None:
        raise _error("entrada_invalida", "Elige un centro MOCK disponible.")
    templates = _read("comparisons.json")
    if not isinstance(templates, dict) or "desconocido" not in templates:
        raise _error("formato_invalido", "Los ejemplos MOCK de comparación están incompletos.")
    results = []
    for item in items:
        data = templates.get(item.material.value, templates["desconocido"])
        template = _validate(ComparisonResult, data)
        results.append(template.model_copy(update={"item_id": item.item_id, "center_id": center_id}))
    payload = {"center_id": center_id, "items": [i.model_dump(mode="json") for i in items]}
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return DeliveryPlan(
        center=center, results=results, generated_at=datetime.now(timezone.utc),
        input_fingerprint=fingerprint,
    )
