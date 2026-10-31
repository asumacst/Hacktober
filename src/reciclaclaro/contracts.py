"""Contratos compartidos de ReciclaClaro.

PROPUESTA — dueña: Rol A (Emilia); aprueba: Rol D (Ángel).
Borrador del Rol C (Noel), ampliado con la propuesta de Emilia por solicitud
de Jose. Pendiente de revision de A, C y D. Explicación en docs/api-contract.md.
Solo cambios aditivos una vez aprobado: no renombrar ni eliminar campos.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, StrictBool, StrictInt, StrictStr, model_validator

Backend = Literal["gemini_api", "local"]
ComparisonStatus = Literal["aceptado", "no_admitido", "pendiente"]
AcceptanceStatus = Literal["accepted", "rejected", "unknown"]
PreparationStatus = Literal["ready", "action_required", "unknown", "not_applicable"]
AttributeName = Literal[
    "material", "presentation", "resin_code", "color", "clean", "residue_free",
    "corrugated", "wet", "greasy", "painted", "boxed", "sorted_by_color",
]
AttributeValue = StrictBool | StrictInt | StrictStr
_STATUS_TO_ACCEPTANCE = {
    "aceptado": "accepted", "no_admitido": "rejected", "pendiente": "unknown",
}
_ACCEPTANCE_TO_STATUS = {value: key for key, value in _STATUS_TO_ACCEPTANCE.items()}
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


class ConfirmedAttribute(BaseModel):
    """Solo hechos confirmados por la persona o un dato sin resolver."""

    value: AttributeValue | None = None
    source: Literal["user_confirmed", "unknown"] = "unknown"

    @model_validator(mode="after")
    def check_confirmation(self) -> ConfirmedAttribute:
        if self.source == "unknown" and self.value is not None:
            raise ValueError("Un atributo desconocido no puede contener un valor confirmado")
        if self.source == "user_confirmed" and self.value is None:
            raise ValueError("La confirmacion del usuario necesita un valor")
        return self


class PendingQuestion(BaseModel):
    attribute: AttributeName
    question: str = Field(min_length=1)


class SourceReference(BaseModel):
    url: str = Field(min_length=1)
    entity: str = Field(min_length=1)
    consulted_on: date
    published_on: date | None = None
    updated_on: date | None = None


class RuleReference(BaseModel):
    rule_id: str = Field(min_length=1)
    sources: list[SourceReference] = Field(min_length=1)


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
    proposed_presentation: str | None = None
    pending_questions: list[PendingQuestion] = Field(default_factory=list)
    analysis_id: str | None = None  # Generado por codigo, igual que item_id.


class IdentificationResult(BaseModel):
    items: list[DetectedItem]
    # Rellenados por código, nunca por el modelo:
    model_id: str
    backend: Backend
    latency_ms: int = Field(ge=0)
    is_mock: bool = False
    analysis_id: str | None = None


# --- Interfaz → Orquestador → Lógica -----------------------------------------

class ConfirmedItem(BaseModel):
    item_id: str
    material: Material
    details: str | None = None  # p. ej. símbolo del plástico confirmado
    user_edited: bool = False
    analysis_id: str | None = None
    revision: int = Field(default=0, ge=0)
    presentation: str | None = None
    attributes: dict[AttributeName, ConfirmedAttribute] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_identity_attributes(self) -> ConfirmedItem:
        # Los campos legados no convierten automaticamente propuestas en hechos.
        for name, expected in (("material", self.material.value),
                               ("presentation", self.presentation)):
            attribute = self.attributes.get(name)
            if attribute is not None and attribute.source == "user_confirmed":
                if attribute.value != expected:
                    raise ValueError(f"El atributo {name} contradice el campo correspondiente")
        return self


class CenterRule(BaseModel):
    material: Material
    status: ComparisonStatus
    preparation: str | None = None
    source_url: str
    consulted_on: date
    rule_id: str | None = None  # Obligatorio para catalogos nuevos; legado compatible.
    presentation: str | None = None
    conditions: dict[AttributeName, AttributeValue] = Field(default_factory=dict)
    preparation_conditions: dict[AttributeName, AttributeValue] = Field(default_factory=dict)
    required_attributes: list[AttributeName] = Field(default_factory=list)
    references: list[SourceReference] = Field(default_factory=list)


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
    analysis_id: str | None = None
    revision: int = Field(default=0, ge=0)
    acceptance: AcceptanceStatus = "unknown"
    preparation_status: PreparationStatus = "unknown"
    preparation_actions: list[str] = Field(default_factory=list)
    missing_data: list[PendingQuestion] = Field(default_factory=list)
    rule_references: list[RuleReference] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def reconcile_legacy_status(cls, data):
        if not isinstance(data, dict):
            return data
        values = dict(data)
        status = values.get("status")
        acceptance = values.get("acceptance")
        if "acceptance" not in values and isinstance(status, str) and status in _STATUS_TO_ACCEPTANCE:
            values["acceptance"] = _STATUS_TO_ACCEPTANCE[status]
        if "status" not in values and isinstance(acceptance, str) and acceptance in _ACCEPTANCE_TO_STATUS:
            values["status"] = _ACCEPTANCE_TO_STATUS[acceptance]
        if values.get("acceptance") == "rejected":
            values.setdefault("preparation_status", "not_applicable")
        return values

    @model_validator(mode="after")
    def check_decision(self) -> ComparisonResult:
        if _STATUS_TO_ACCEPTANCE[self.status] != self.acceptance:
            raise ValueError("status y acceptance deben representar la misma decision")
        if self.acceptance == "rejected" and self.preparation_status != "not_applicable":
            raise ValueError("Un rechazo requiere preparacion no aplicable")
        if self.acceptance == "rejected" and self.preparation_actions:
            raise ValueError("Un rechazo no debe prometer aceptacion mediante preparacion")
        if self.acceptance != "rejected" and self.preparation_status == "not_applicable":
            raise ValueError("La preparacion no aplicable se reserva para rechazos")
        if self.preparation_status in ("ready", "action_required") and self.acceptance != "accepted":
            raise ValueError("Evaluar preparacion requiere aceptacion documentada")
        if self.preparation_status == "ready" and (self.missing_data or self.preparation_actions):
            raise ValueError("Un objeto listo no puede tener datos o acciones pendientes")
        if self.preparation_status == "ready" and not self.rule_references:
            raise ValueError("Un objeto listo necesita referencias a las reglas aplicadas")
        if self.preparation_status == "action_required" and not self.preparation_actions:
            raise ValueError("La preparacion pendiente necesita una accion")
        return self


class DeliveryPlan(BaseModel):
    center: Center
    results: list[ComparisonResult]
    generated_at: datetime
    input_fingerprint: str  # cambia si cambian foto, materiales o centro
    analysis_id: str | None = None
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_result_context(self) -> DeliveryPlan:
        for result in self.results:
            if result.center_id != self.center.center_id:
                raise ValueError("El resultado pertenece a otro centro")
            if result.revision != self.revision:
                raise ValueError("El resultado pertenece a otra revision")
            if result.analysis_id != self.analysis_id:
                raise ValueError("El resultado pertenece a otro analisis")
        return self


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
