"""Contratos compartidos de ReciclaClaro.

PROPUESTA — dueña: Rol A (Emilia); aprueba: Rol D (Ángel).
Borrador redactado por el Rol C (Noel) para que las cuatro capas trabajen en
paralelo. Explicación y ejemplos en docs/api-contract.md.
Solo cambios aditivos una vez aprobado: no renombrar ni eliminar campos.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

Backend = Literal["gemini_api", "local"]
ComparisonStatus = Literal["aceptado", "no_admitido", "pendiente"]
ErrorCategory = Literal["api", "timeout", "formato_invalido", "entrada_invalida", "sin_datos"]


class Material(str, Enum):
    """Lista corta inicial; la ajustan A y B según el catálogo."""

    PET_1 = "PET_1"
    HDPE_2 = "HDPE_2"
    PP_5 = "PP_5"
    ALUMINIO = "aluminio"
    VIDRIO = "vidrio"
    PAPEL_CARTON = "papel_carton"
    DESCONOCIDO = "desconocido"


# --- Interfaz → Orquestador → IA ---------------------------------------------

class AnalysisRequest(BaseModel):
    image_bytes: bytes
    mime_type: Literal["image/jpeg", "image/png", "image/webp"]
    backend: Backend = "gemini_api"


class DetectedItem(BaseModel):
    item_id: str
    description: str
    proposed_material: Material
    visible_evidence: str
    pending_question: str | None = None


class IdentificationResult(BaseModel):
    items: list[DetectedItem]
    # Rellenados por código, nunca por el modelo:
    model_id: str
    backend: Backend
    latency_ms: int = Field(ge=0)
    is_mock: bool = False


# --- Interfaz → Orquestador → Lógica -----------------------------------------

class ConfirmedItem(BaseModel):
    item_id: str
    material: Material
    details: str | None = None  # p. ej. símbolo del plástico confirmado
    user_edited: bool = False


class CenterRule(BaseModel):
    material: Material
    status: ComparisonStatus
    preparation: str | None = None
    source_url: str
    consulted_on: date


class Center(BaseModel):
    center_id: str
    name: str
    rules: list[CenterRule]
    source_url: str
    consulted_on: date


class ComparisonResult(BaseModel):
    item_id: str
    center_id: str
    status: ComparisonStatus
    reason: str
    preparation: str | None = None
    rule_source_url: str | None = None  # None si no hay regla documentada
    consulted_on: date | None = None


class DeliveryPlan(BaseModel):
    center: Center
    results: list[ComparisonResult]
    generated_at: datetime
    input_fingerprint: str  # cambia si cambian foto, materiales o centro


# --- Errores ------------------------------------------------------------------

class AppError(BaseModel):
    category: ErrorCategory
    message: str  # texto utilizable por la persona usuaria
    retryable: bool


class ReciclaClaroError(Exception):
    """Error que el orquestador lanza hacia la interfaz."""

    def __init__(self, error: AppError) -> None:
        super().__init__(error.message)
        self.error = error
