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


MATERIAL_UI = {
    "PET_1": "Plástico PET (1)", "HDPE_2": "Plástico HDPE (2)", "PP_5": "Plástico PP (5)",
    "aluminio": "Aluminio", "vidrio": "Vidrio", "papel_carton": "Papel o cartón", "desconocido": "No sé",
}
PRESENTATION_UI = {
    "botella": "Botella", "envase": "Envase o frasco", "tapita": "Tapita",
    "envase_huevos": "Envase de huevos", "envase_ensalada": "Envase de ensalada",
    "envase_ketchup": "Envase de ketchup", "envase_sirope": "Envase de sirope",
    "caja": "Caja armada", "caja_desarmada": "Caja desarmada", "espejo": "Espejo",
    "ventana": "Ventana", "puerta_vidrio": "Puerta de vidrio", "mesa_vidrio": "Mesa de vidrio",
}
# Preguntas de sí/no que el catálogo puede exigir; el orden es el de la pantalla.
CHECK_UI = {
    "clean": "¿Está limpio?",
    "residue_free": "¿Sin restos de comida u otros residuos?",
    "sorted_by_color": "¿Lo separaste por color?",
    "boxed": "¿Lo llevas dentro de una caja?",
    "corrugated": "¿Es cartón corrugado (con ondas por dentro)?",
    "wet": "¿Está mojado?",
    "greasy": "¿Tiene grasa?",
    "painted": "¿Está pintado?",
}
PLASTICS = {Material.PET_1, Material.HDPE_2, Material.PP_5}


def catalog_fields(centers: list[Center], material: Material) -> tuple[list[str], list[str], bool]:
    """Presentaciones, preguntas de sí/no y si pide símbolo, según las reglas del catálogo.

    La interfaz no decide nada: solo pregunta lo que alguna regla del material consulta.
    """
    presentations: list[str] = []
    checks: set[str] = set()
    needs_resin = material in PLASTICS or material == Material.DESCONOCIDO
    for rule in (r for c in centers for r in c.rules if r.material == material):
        if rule.presentation and rule.presentation not in presentations:
            presentations.append(rule.presentation)
        names = {*rule.conditions, *rule.preparation_conditions, *rule.required_attributes}
        checks |= names & CHECK_UI.keys()
        needs_resin |= "resin_code" in names
    return presentations, [n for n in CHECK_UI if n in checks], needs_resin


def _confirmed_item(row: dict, original: DetectedItem, analysis_id: str | None) -> ConfirmedItem:
    """Solo marca como confirmado lo que la persona indicó; nada se copia de Gemma."""
    attributes: dict[str, ConfirmedAttribute] = {}
    presentation = row.get("Presentación")
    if presentation == UNKNOWN:
        presentation = None
    if row["Confirmo"]:
        attributes["material"] = ConfirmedAttribute(value=row["Material"], source="user_confirmed")
        if presentation is not None:
            attributes["presentation"] = ConfirmedAttribute(value=presentation, source="user_confirmed")
    if row["Símbolo"] is not None:
        attributes["resin_code"] = ConfirmedAttribute(value=int(row["Símbolo"]), source="user_confirmed")
    answers = {"clean": row["¿Limpio?"], **row.get("checks", {})}
    for name, answer in answers.items():
        if YES_NO[answer] is not None:
            attributes[name] = ConfirmedAttribute(value=YES_NO[answer], source="user_confirmed")
    return ConfirmedItem(
        item_id=row["item_id"],
        analysis_id=analysis_id,
        material=Material(row["Material"]),
        # Sin «Confirmo» la presentación sigue siendo una propuesta y no se envía.
        presentation=presentation if row["Confirmo"] else None,
        user_edited=row["Material"] != original.proposed_material.value or bool(attributes),
        attributes=attributes,
    )


def _item_form(item: DetectedItem, centers: list[Center], key: str) -> dict:
    """Ficha de un objeto: solo muestra las preguntas que el catálogo usa para su material."""
    with st.container(border=True):
        st.markdown(f"**{item.description}**")
        st.caption(f"Evidencia: {item.visible_evidence}")
        if questions := _questions(item):
            st.caption(f"❓ {questions}")
        materials = [m.value for m in Material]
        material = st.selectbox("Material", materials, key=f"{key}-material",
                                index=materials.index(item.proposed_material.value),
                                format_func=lambda v: MATERIAL_UI.get(v, v))
        presentations, checks, needs_resin = catalog_fields(centers, Material(material))
        row = {"item_id": item.item_id, "Material": material, "Presentación": UNKNOWN,
               "Símbolo": None, "¿Limpio?": UNKNOWN, "checks": {}}
        if presentations:
            options = [UNKNOWN, *presentations]
            proposed = item.proposed_presentation
            row["Presentación"] = st.selectbox(
                "¿Qué es?", options, key=f"{key}-presentation-{material}",
                index=options.index(proposed) if proposed in options else 0,
                format_func=lambda v: PRESENTATION_UI.get(v, v.replace("_", " ").capitalize()))
        if needs_resin:
            row["Símbolo"] = st.number_input(
                "Número dentro del símbolo de reciclaje (1–7)", min_value=1, max_value=7, step=1,
                value=None, key=f"{key}-resin", placeholder="Déjalo vacío si no lo ves")
        for name in checks:
            answer = st.radio(CHECK_UI[name], list(YES_NO), horizontal=True, key=f"{key}-{name}-{material}")
            if name == "clean":
                row["¿Limpio?"] = answer
            else:
                row["checks"][name] = answer
        row["Confirmo"] = st.checkbox("Revisé el material y lo que es", key=f"{key}-confirm")
    return row


def review(result: IdentificationResult, centers: list[Center],
           key: str = "review") -> tuple[list[ConfirmedItem], bool]:
    """Ficha por objeto. Devuelve el borrador actual y si se pulsó «Confirmar materiales»."""
    st.subheader("2. Revisa lo que identificó Gemma")
    st.caption("Corrige el material, indica qué es y responde lo que sepas. "
               "«No sé» queda como dato pendiente: no lo inventamos.")
    rows = [_item_form(i, centers, f"{key}-{i.item_id}") for i in result.items]
    originals = {i.item_id: i for i in result.items}
    unconfirmed = [originals[r["item_id"]].description for r in rows if not r["Confirmo"]]
    if unconfirmed:
        st.warning("Sin confirmar: " + ", ".join(unconfirmed)
                   + ". Puedes continuar; el centro no podrá decidir con datos sin confirmar.")
    draft = [_confirmed_item(r, originals[r["item_id"]], result.analysis_id) for r in rows]
    return draft, st.button("Confirmar materiales", type="primary")


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
    elif r.missing_data:
        lines.append("Completa estos datos en el paso 2 y vuelve a generar el plan.")
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
