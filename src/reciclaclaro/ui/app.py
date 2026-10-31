"""Interfaz de ReciclaClaro. Ejecutar: streamlit run src/reciclaclaro/ui/app.py"""

from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

# Permite `streamlit run` sin instalar el paquete (la estructura la define el Rol D).
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from reciclaclaro.contracts import (  # noqa: E402
    AnalysisRequest, AppError, Center, CenterRule, ComparisonResult, DeliveryPlan,
    DetectedItem, IdentificationResult, Material, ReciclaClaroError,
)
from reciclaclaro.ui import components as ui  # noqa: E402
from reciclaclaro.ui import state  # noqa: E402

try:
    from reciclaclaro.ui import client  # adaptador mock/live (worktree de Codex)
except ImportError:
    client = None


# TEMPORAL: adaptador mínimo mientras llega ui/client.py desde feature/noel-codex.
# Eliminar al integrar. Todo lo que devuelve es MOCK.
class _TemporalClient:
    _CENTER = Center(
        center_id="centro-ejemplo", name="Centro de ejemplo (MOCK)",
        source_url="https://example.org/centro-ejemplo", consulted_on=date(2026, 10, 31),
        rules=[
            CenterRule(material=Material.PET_1, status="aceptado", preparation="Vacía, enjuaga y aplasta la botella.",
                       source_url="https://example.org/centro-ejemplo#pet", consulted_on=date(2026, 10, 31)),
            CenterRule(material=Material.ALUMINIO, status="aceptado", preparation="Enjuaga y seca la lata.",
                       source_url="https://example.org/centro-ejemplo#aluminio", consulted_on=date(2026, 10, 31)),
            CenterRule(material=Material.VIDRIO, status="no_admitido", preparation=None,
                       source_url="https://example.org/centro-ejemplo#vidrio", consulted_on=date(2026, 10, 31)),
        ],
    )

    def identify(self, req: AnalysisRequest) -> IdentificationResult:
        return IdentificationResult(
            items=[
                DetectedItem(item_id="obj-1", description="Botella transparente", proposed_material=Material.PET_1,
                             visible_evidence="Símbolo 1 visible en la base"),
                DetectedItem(item_id="obj-2", description="Lata", proposed_material=Material.ALUMINIO,
                             visible_evidence="Forma y brillo metálico"),
                DetectedItem(item_id="obj-3", description="Envase blanco sin símbolo",
                             proposed_material=Material.DESCONOCIDO, visible_evidence="No se distingue el símbolo",
                             pending_question="¿Qué número tiene el símbolo de reciclaje?"),
            ],
            model_id="mock", backend=req.backend, latency_ms=0, is_mock=True,
        )

    def list_centers(self) -> list[Center]:
        return [self._CENTER]

    def compare(self, items, center_id: str) -> DeliveryPlan:
        rules = {r.material: r for r in self._CENTER.rules}
        results = []
        for item in items:
            rule = rules.get(item.material)
            if rule is None:
                results.append(ComparisonResult(item_id=item.item_id, center_id=center_id, status="pendiente",
                                                reason="El catálogo no tiene una regla para este material."))
            else:
                results.append(ComparisonResult(
                    item_id=item.item_id, center_id=center_id, status=rule.status,
                    reason="Según las condiciones documentadas del centro.", preparation=rule.preparation,
                    rule_source_url=rule.source_url, consulted_on=rule.consulted_on))
        return DeliveryPlan(center=self._CENTER, results=results, generated_at=datetime.now(),
                            input_fingerprint="mock")


api = client if client is not None else _TemporalClient()


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

confirmed = ui.review(result)
if confirmed is not None:
    ss.confirmed = confirmed
if ss.confirmed is None:
    ui.model_footer(result)
    st.stop()

centers = call(api.list_centers) or []
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
