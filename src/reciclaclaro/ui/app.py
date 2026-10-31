"""Interfaz de ReciclaClaro. Ejecutar: streamlit run src/reciclaclaro/ui/app.py"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Permite `streamlit run` sin instalar el paquete (la estructura la define el Rol D).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from reciclaclaro.contracts import (  # noqa: E402
    AnalysisRequest, AppError, Center, ConfirmedItem, DeliveryPlan, IdentificationResult,
    ReciclaClaroError,
)
from reciclaclaro.logic import compare_items, load_centers  # noqa: E402
from reciclaclaro.ui import components as ui  # noqa: E402
from reciclaclaro.ui import state  # noqa: E402

from reciclaclaro.ui import client  # noqa: E402


# TEMPORAL hasta que exista el orquestador de Ángel: en modo mock, client.py replica
# identificaciones MOCK, pero los centros y la comparación usan el catálogo y el
# comparador reales de José (logic/) en lugar de los fixtures ficticios.
# En modo live todo pasa por client.py → reciclaclaro.orchestrator.
class _CatalogClient:
    identify = staticmethod(client.identify)

    def list_centers(self) -> list[Center]:
        return load_centers()

    def compare(self, items: list[ConfirmedItem], center_id: str) -> DeliveryPlan:
        center = next((c for c in self.list_centers() if c.center_id == center_id), None)
        if center is None:
            raise ReciclaClaroError(AppError(category="entrada_invalida",
                                             message="Elige un centro del catálogo.", retryable=False))
        payload = json.dumps([i.model_dump(mode="json") for i in items] + [center_id], sort_keys=True)
        return DeliveryPlan(center=center, results=compare_items(items, center), generated_at=datetime.now(),
                            input_fingerprint=hashlib.sha256(payload.encode()).hexdigest(),
                            analysis_id=items[0].analysis_id if items else None,
                            revision=items[0].revision if items else 0)


api = client if os.environ.get("RECICLACLARO_UI_MODE", "mock").strip().lower() == "live" else _CatalogClient()


def call(fn, *args):
    """Ejecuta una llamada al adaptador y guarda el error para la interfaz."""
    try:
        st.session_state.error = None
        return fn(*args)
    except ReciclaClaroError as exc:
        st.session_state.error = exc.error
    except Exception:  # noqa: BLE001 — la UI nunca debe romperse en la demo
        st.session_state.error = AppError(category="api", message="Algo salió mal al procesar la solicitud. "
                                          "Intenta de nuevo en unos segundos.", retryable=True)
    return None


st.set_page_config(page_title="ReciclaClaro", page_icon="♻️", layout="centered")
state.init(st.session_state)
ss = st.session_state

with st.sidebar:
    st.header("Ajustes")
    backend = st.radio("Proveedor de Gemma 4", ["gemini_api", "local"],
                       format_func=ui.BACKEND_LABEL.get,
                       help="El modo local usa Ollama en esta máquina. El reto exige la Gemini API.")

ui.header()

photo = ui.uploader()
if photo is None:
    st.stop()
image_bytes, mime = photo
if ss.image_bytes != image_bytes:
    state.on_new_photo(ss, image_bytes, mime)
state.on_backend(ss, backend)

if st.button("Identificar materiales", type="primary", disabled=ss.identification is not None):
    with st.status("Gemma está analizando la foto…", expanded=False) as status:
        ss.identification = call(api.identify, AnalysisRequest(image_bytes=image_bytes, mime_type=mime,
                                                                backend=backend))
        status.update(label="Análisis terminado" if ss.identification else "No se pudo analizar la foto",
                      state="complete" if ss.identification else "error")

if ss.error is not None and ss.identification is None:
    if ui.error(ss.error):
        ss.error = None
        st.rerun()
    st.stop()

result: IdentificationResult | None = ss.identification
if result is None:
    st.stop()
if result.is_mock:
    ui.mock_banner()

centers = call(api.list_centers)
if centers is None:  # fallo al cargar el catálogo: distinto de un catálogo vacío
    if ui.error(ss.error):
        ss.error = None
        st.rerun()
    ui.model_footer(result)
    st.stop()
if not centers:
    st.warning("El catálogo no tiene centros de acopio documentados todavía. "
               "Sin un centro no podemos comparar tus materiales.")
    ui.model_footer(result)
    st.stop()

# La clave incluye foto y proveedor para no arrastrar respuestas de otro análisis.
review_key = f"{state.fingerprint(image_bytes, [], None)[:12]}-{backend}"
draft, submitted = ui.review(result, centers, key=review_key)
if submitted:
    ss.confirmed = draft
if ss.confirmed is None:
    ui.model_footer(result)
    st.stop()
if state.has_pending_edits(ss, draft):
    st.warning("Tienes cambios sin confirmar. Pulsa «Confirmar materiales» para generar un plan actualizado.")
    ui.model_footer(result)
    st.stop()

center_id = ui.center_picker(centers)
if center_id is None:
    ui.model_footer(result)
    st.stop()

current_fp = state.fingerprint(image_bytes, ss.confirmed, center_id)
if st.button("Generar plan de entrega", type="primary"):
    ss.plan = call(api.compare, ss.confirmed, center_id)
    ss.plan_fp = current_fp if ss.plan else None

if ss.error is not None:
    if ui.error(ss.error):
        ss.error = None
        st.rerun()
elif state.plan_is_current(ss, current_fp):
    ui.plan(ss.plan, {i.item_id: i.description for i in result.items})
elif ss.plan is not None:
    st.info("Cambiaste los materiales o el centro. Vuelve a generar el plan para verlo actualizado.")

ui.model_footer(result)
