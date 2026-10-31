"""Orquestador de ReciclaClaro: une interfaz, IA y lógica, y controla los errores.

Dueño: Rol D (Ángel). Firmas según docs/api-contract.md. La interfaz llama solo
a estas tres funciones; no importa la capa de IA ni la lógica directamente.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError

from reciclaclaro.contracts import (
    AnalysisRequest, AppError, Center, ConfirmedItem, DeliveryPlan, DetectedItem,
    IdentificationResult, Material, ReciclaClaroError,
)
from reciclaclaro.logic import compare_items, load_centers

# Mismo límite que valida la capa de IA del Rol A.
MAX_IMAGE_BYTES = 8 * 1024 * 1024
# Capa de IA del Rol A: identify(req, *, mock=False) -> IdentificationResult.
AI_MODULE = "reciclaclaro.ai"
# Con RECICLACLARO_AI_MOCK=1 se pide a la IA su muestra etiquetada, sin red ni clave.
AI_MOCK_ENV = "RECICLACLARO_AI_MOCK"
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

# Las variables ya definidas en el entorno tienen prioridad sobre el archivo .env.
load_dotenv(ENV_FILE, override=False)


def _fail(category, message, retryable):
    return ReciclaClaroError(AppError(category=category, message=message, retryable=retryable))


def _load_ai():
    """Capa de IA del Rol A, o None mientras no exista (se usa el modo MOCK etiquetado)."""
    try:
        return importlib.import_module(AI_MODULE)
    except ModuleNotFoundError as exc:
        if exc.name != AI_MODULE:
            raise  # existe la capa, pero le falta una dependencia
        return None


def _mock_identification(req: AnalysisRequest) -> IdentificationResult:
    """Respuesta fija mientras no exista la capa de IA. No analiza la foto."""
    evidence = "Ejemplo fijo (MOCK): la foto no fue analizada"
    return IdentificationResult(
        items=[
            DetectedItem(item_id="obj-1", description="Botella transparente (MOCK)",
                         proposed_material=Material.PET_1, visible_evidence=evidence),
            DetectedItem(item_id="obj-2", description="Envase sin símbolo visible (MOCK)",
                         proposed_material=Material.DESCONOCIDO, visible_evidence=evidence,
                         pending_question="¿Qué número tiene el símbolo de reciclaje?"),
        ],
        model_id="mock", backend=req.backend, latency_ms=0, is_mock=True,
    )


def identify(req: AnalysisRequest) -> IdentificationResult:
    """Validar la foto, pedir la identificación a la IA y rellenar los campos de código."""
    if not isinstance(req, AnalysisRequest):
        raise _fail("entrada_invalida", "La solicitud de análisis no es válida.", False)
    if not req.image_bytes:
        raise _fail("entrada_invalida", "La foto está vacía. Sube otra imagen.", False)
    if len(req.image_bytes) > MAX_IMAGE_BYTES:
        raise _fail("entrada_invalida", "La foto supera 8 MB. Sube una imagen más liviana.", False)
    try:
        ai = _load_ai()
    except ImportError as exc:
        raise _fail("api", "No se pudo cargar el módulo de IA. Revisa la instalación.", False) from exc

    use_mock = os.getenv(AI_MOCK_ENV, "").strip().lower() in {"1", "true", "si", "sí"}
    started = time.monotonic()
    if ai is None:
        result = _mock_identification(req)
    else:
        try:
            result = ai.identify(req, mock=True) if use_mock else ai.identify(req)
        except ReciclaClaroError:
            raise
        except TimeoutError as exc:
            raise _fail("timeout", "Gemma tardó demasiado en responder. Intenta de nuevo.", True) from exc
        except Exception as exc:  # noqa: BLE001 — cualquier fallo del proveedor llega como AppError
            raise _fail("api", "No se pudo analizar la foto con Gemma. Intenta de nuevo.", True) from exc
        if not isinstance(result, IdentificationResult):
            raise _fail("formato_invalido", "La respuesta del modelo no tiene el formato esperado.", True)
    if not result.items:
        raise _fail("sin_datos", "No se identificaron objetos. Prueba con otra foto más cercana.", True)

    # Campos que rellena el código, nunca el modelo. Se respeta el analysis_id
    # que ya generó la capa de IA y se propaga a todos los objetos.
    analysis_id = result.analysis_id or uuid.uuid4().hex
    return result.model_copy(update={
        "items": [item.model_copy(update={"analysis_id": analysis_id}) for item in result.items],
        "analysis_id": analysis_id,
        "backend": req.backend,
        "latency_ms": int((time.monotonic() - started) * 1000),
    })


def list_centers() -> list[Center]:
    """Centros del catálogo documentado del Rol B."""
    return load_centers()


def _fingerprint(items: list[ConfirmedItem], center_id: str) -> str:
    # El analysis_id de cada objeto liga la huella a la foto analizada.
    payload = {
        "center_id": center_id,
        "items": sorted((item.model_dump(mode="json") for item in items), key=lambda d: d["item_id"]),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def compare(items: list[ConfirmedItem], center_id: str) -> DeliveryPlan:
    """Comparar los materiales confirmados con un centro y armar el plan de entrega."""
    if not isinstance(items, list) or not items:
        raise _fail("entrada_invalida", "Confirma al menos un objeto antes de generar el plan.", False)
    center = next((c for c in load_centers() if c.center_id == center_id), None)
    if center is None:
        raise _fail("entrada_invalida", "El centro elegido no está en el catálogo.", False)
    results = compare_items(items, center)
    try:
        return DeliveryPlan(
            center=center, results=results, generated_at=datetime.now(timezone.utc),
            input_fingerprint=_fingerprint(items, center_id),
            analysis_id=items[0].analysis_id, revision=items[0].revision,
        )
    except ValidationError as exc:
        raise _fail("formato_invalido", "El plan generado no es coherente. Vuelve a confirmar los objetos.",
                    False) from exc
