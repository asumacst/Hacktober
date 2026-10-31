"""Piezas visuales de la interfaz. Solo presentan datos de los contratos."""

from __future__ import annotations

import streamlit as st

from reciclaclaro.contracts import (
    AppError, Center, ConfirmedItem, DeliveryPlan, IdentificationResult, Material,
)

MAX_MB = 8
STATUS_UI = {
    "aceptado": ("✅", "Aceptado", st.success),
    "no_admitido": ("⛔", "No admitido", st.error),
    "pendiente": ("❓", "Pendiente de confirmar", st.warning),
}
BACKEND_LABEL = {"gemini_api": "Gemini API", "local": "Local (Ollama)"}


def header() -> None:
    st.title("♻️ ReciclaClaro")
    st.caption("Fotografía tus residuos, confirma los materiales y descubre cómo entregarlos "
               "en un centro de acopio de Panamá.")


def mock_banner() -> None:
    st.info("**Modo de ejemplo (MOCK):** estas respuestas son datos de prueba, no un análisis real de Gemma.",
            icon="🧪")


def uploader() -> tuple[bytes, str] | None:
    st.subheader("1. Sube una foto")
    file = st.file_uploader(
        "Foto de tus residuos (pocos objetos, buena luz, símbolos visibles)",
        type=["jpg", "jpeg", "png", "webp"],
    )
    if file is None:
        return None
    if file.size > MAX_MB * 1024 * 1024:
        st.error(f"La foto pesa más de {MAX_MB} MB. Prueba con una imagen más pequeña.")
        return None
    st.image(file, width=320)
    mime = "image/jpeg" if file.type == "image/jpg" else file.type
    return file.getvalue(), mime


def review(result: IdentificationResult) -> list[ConfirmedItem] | None:
    """Tabla editable. Devuelve los materiales confirmados al pulsar el botón."""
    st.subheader("2. Revisa lo que identificó Gemma")
    st.caption("Corrige el material si es necesario. Si ves el símbolo de reciclaje, anótalo en «Detalle».")
    rows = [{
        "item_id": i.item_id,
        "Objeto": i.description,
        "Evidencia": i.visible_evidence,
        "Material": i.proposed_material.value,
        "Detalle": "",
        "Duda": i.pending_question or "",
    } for i in result.items]
    edited = st.data_editor(
        rows,
        key="review_editor",
        hide_index=True,
        disabled=["item_id", "Objeto", "Evidencia", "Duda"],
        column_order=["Objeto", "Evidencia", "Material", "Detalle", "Duda"],
        column_config={
            "Material": st.column_config.SelectboxColumn(
                "Material", options=[m.value for m in Material], required=True),
            "Detalle": st.column_config.TextColumn("Detalle (símbolo, estado)"),
            "Duda": st.column_config.TextColumn("Pregunta pendiente"),
        },
        width="stretch",
    )
    pending = [r["Objeto"] for r in edited if r["Duda"] and not r["Detalle"]]
    if pending:
        st.warning("Hay dudas sin responder: " + ", ".join(pending)
                   + ". Puedes continuar; esos objetos quedarán como pendientes.")
    if not st.button("Confirmar materiales", type="primary"):
        return None
    originals = {i.item_id: i.proposed_material.value for i in result.items}
    return [ConfirmedItem(
        item_id=r["item_id"],
        material=Material(r["Material"]),
        details=r["Detalle"] or None,
        user_edited=r["Material"] != originals[r["item_id"]] or bool(r["Detalle"]),
    ) for r in edited]


def center_picker(centers: list[Center]) -> str | None:
    st.subheader("3. Elige el centro de acopio")
    if not centers:
        st.warning("Todavía no hay centros documentados en el catálogo.")
        return None
    by_id = {c.center_id: c for c in centers}
    center_id = st.selectbox("Centro de acopio", list(by_id), format_func=lambda cid: by_id[cid].name)
    c = by_id[center_id]
    st.caption(f"Reglas consultadas el {c.consulted_on:%d/%m/%Y} · [Fuente]({c.source_url})")
    return center_id


def plan(p: DeliveryPlan, names: dict[str, str]) -> None:
    st.subheader(f"4. Tu plan para {p.center.name}")
    counts = {s: sum(r.status == s for r in p.results) for s in STATUS_UI}
    cols = st.columns(3)
    for col, (status, (icon, label, _)) in zip(cols, STATUS_UI.items()):
        col.metric(f"{icon} {label}", counts[status])
    for r in p.results:
        icon, label, box = STATUS_UI[r.status]
        text = f"**{icon} {names.get(r.item_id, r.item_id)} — {label}**\n\n{r.reason}"
        if r.preparation:
            text += f"\n\n**Cómo prepararlo:** {r.preparation}"
        if r.rule_source_url and r.consulted_on:
            text += f"\n\n[Fuente de la regla]({r.rule_source_url}) · consultada el {r.consulted_on:%d/%m/%Y}"
        else:
            text += "\n\nSin regla documentada para este material: confirma con el centro antes de llevarlo."
        box(text)
    st.caption("Plan basado en el catálogo documentado. No garantiza disponibilidad en tiempo real.")


def error(err: AppError) -> bool:
    """Muestra el error. Devuelve True si la persona pide reintentar."""
    st.error(err.message, icon="⚠️")
    return err.retryable and st.button("Reintentar")


def model_footer(result: IdentificationResult) -> None:
    st.divider()
    st.caption(f"Powered by Gemma 4 via Gemini API · Modelo: `{result.model_id}` · "
               f"Proveedor: {BACKEND_LABEL[result.backend]} · {result.latency_ms / 1000:.1f} s"
               + (" · respuesta de ejemplo" if result.is_mock else ""))
