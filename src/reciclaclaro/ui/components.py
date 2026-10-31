"""Piezas visuales de la interfaz. Solo presentan datos de los contratos."""

from __future__ import annotations

import streamlit as st

from reciclaclaro.contracts import (
    AppError, Center, ComparisonResult, ConfirmedAttribute, ConfirmedItem, DeliveryPlan,
    DetectedItem, IdentificationResult, Material,
)

MAX_MB = 8
UNKNOWN = "No sé"
YES_NO = {UNKNOWN: None, "Sí": True, "No": False}
PREPARATION_UI = {
    "ready": "Listo para llevar",
    "action_required": "Requiere preparación",
    "unknown": "Preparación sin confirmar",
}
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


def _questions(item: DetectedItem) -> str:
    texts = [q.question for q in item.pending_questions]
    if item.pending_question and item.pending_question not in texts:
        texts.insert(0, item.pending_question)
    return " · ".join(texts)


def _confirmed_item(row: dict, original: DetectedItem, analysis_id: str | None) -> ConfirmedItem:
    """Solo marca como confirmado lo que la persona indicó; nada se copia de Gemma."""
    attributes: dict[str, ConfirmedAttribute] = {}
    if row["Confirmo"]:
        attributes["material"] = ConfirmedAttribute(value=row["Material"], source="user_confirmed")
    if row["Símbolo"] is not None:
        attributes["resin_code"] = ConfirmedAttribute(value=int(row["Símbolo"]), source="user_confirmed")
    if YES_NO[row["¿Limpio?"]] is not None:
        attributes["clean"] = ConfirmedAttribute(value=YES_NO[row["¿Limpio?"]], source="user_confirmed")
    return ConfirmedItem(
        item_id=row["item_id"],
        analysis_id=analysis_id,
        material=Material(row["Material"]),
        user_edited=row["Material"] != original.proposed_material.value or bool(attributes),
        attributes=attributes,
    )


def review(result: IdentificationResult) -> list[ConfirmedItem] | None:
    """Tabla editable. Devuelve los materiales confirmados al pulsar el botón."""
    st.subheader("2. Revisa lo que identificó Gemma")
    st.caption("Corrige el material y marca «Confirmo» en cada objeto que revisaste. "
               "Si ves el número dentro del símbolo de reciclaje, anótalo.")
    rows = [{
        "item_id": i.item_id,
        "Objeto": i.description,
        "Evidencia": i.visible_evidence,
        "Material": i.proposed_material.value,
        "Confirmo": False,
        "Símbolo": None,
        "¿Limpio?": UNKNOWN,
        "Duda": _questions(i),
    } for i in result.items]
    edited = st.data_editor(
        rows,
        key="review_editor",
        hide_index=True,
        disabled=["item_id", "Objeto", "Evidencia", "Duda"],
        column_order=["Objeto", "Evidencia", "Material", "Confirmo", "Símbolo", "¿Limpio?", "Duda"],
        column_config={
            "Material": st.column_config.SelectboxColumn(
                "Material", options=[m.value for m in Material], required=True),
            "Confirmo": st.column_config.CheckboxColumn("Confirmo", help="Revisé este objeto y su material"),
            "Símbolo": st.column_config.NumberColumn("Símbolo (1–7)", min_value=1, max_value=7, step=1),
            "¿Limpio?": st.column_config.SelectboxColumn("¿Limpio?", options=list(YES_NO), required=True),
            "Duda": st.column_config.TextColumn("Pregunta pendiente"),
        },
        width="stretch",
    )
    unconfirmed = [r["Objeto"] for r in edited if not r["Confirmo"]]
    if unconfirmed:
        st.warning("Sin confirmar: " + ", ".join(unconfirmed)
                   + ". Puedes continuar; el centro no podrá decidir con datos sin confirmar.")
    if not st.button("Confirmar materiales", type="primary"):
        return None
    originals = {i.item_id: i for i in result.items}
    return [_confirmed_item(r, originals[r["item_id"]], result.analysis_id) for r in edited]


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
        _result_card(r, names.get(r.item_id, r.item_id))
    st.caption("Plan basado en el catálogo documentado. No garantiza disponibilidad en tiempo real.")


def _result_card(r: ComparisonResult, name: str) -> None:
    icon, label, box = STATUS_UI[r.status]
    if r.acceptance == "accepted":
        label = f"{label} · {PREPARATION_UI[r.preparation_status]}"
        if r.preparation_status == "action_required":
            icon, box = "🧽", st.info
    lines = [f"**{icon} {name} — {label}**", r.reason]
    if r.preparation_actions:
        lines.append("**Antes de llevarlo:**\n" + "\n".join(f"- {a}" for a in r.preparation_actions))
    elif r.preparation:
        lines.append(f"**Cómo prepararlo:** {r.preparation}")
    if r.missing_data:
        lines.append("**Falta confirmar:**\n" + "\n".join(f"- {q.question}" for q in r.missing_data))
    sources = [s for ref in r.rule_references for s in ref.sources]
    if sources:
        lines.append(" · ".join(f"[{s.entity}]({s.url}) (consultada el {s.consulted_on:%d/%m/%Y})"
                                for s in sources))
    elif r.rule_source_url and r.consulted_on:
        lines.append(f"[Fuente de la regla]({r.rule_source_url}) · consultada el {r.consulted_on:%d/%m/%Y}")
    else:
        lines.append("Sin regla documentada para este material: confirma con el centro antes de llevarlo.")
    box("\n\n".join(lines))


def error(err: AppError) -> bool:
    """Muestra el error. Devuelve True si la persona pide reintentar."""
    st.error(err.message, icon="⚠️")
    return err.retryable and st.button("Reintentar")


def model_footer(result: IdentificationResult) -> None:
    st.divider()
    st.caption(f"Powered by Gemma 4 via Gemini API · Modelo: `{result.model_id}` · "
               f"Proveedor: {BACKEND_LABEL[result.backend]} · {result.latency_ms / 1000:.1f} s"
               + (" · respuesta de ejemplo" if result.is_mock else ""))
