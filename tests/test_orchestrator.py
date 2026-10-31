"""Orquestador: validación, errores y armado del plan, sin red ni cuota de Gemini."""

import types

import pytest

from reciclaclaro import orchestrator
from reciclaclaro.contracts import (
    AnalysisRequest, AppError, ConfirmedItem, DetectedItem, IdentificationResult, Material,
    ReciclaClaroError,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
CENTER_ID = orchestrator.list_centers()[0].center_id


def request(data=PNG, backend="gemini_api"):
    return AnalysisRequest(image_bytes=data, mime_type="image/png", backend=backend)


def use_ai(monkeypatch, identify):
    monkeypatch.setattr(orchestrator, "_load_ai", lambda: types.SimpleNamespace(identify=identify))


def item(item_id="obj-1", material=Material.DESCONOCIDO, analysis_id="a1", revision=0):
    return ConfirmedItem(item_id=item_id, material=material, analysis_id=analysis_id, revision=revision)


def error_of(call, *args):
    with pytest.raises(ReciclaClaroError) as exc:
        call(*args)
    return exc.value.error


@pytest.fixture
def no_ai(monkeypatch):
    monkeypatch.setattr(orchestrator, "_load_ai", lambda: None)


# --- identify ------------------------------------------------------------------

def test_without_ai_layer_returns_mock_labeled_as_such(no_ai):
    result = orchestrator.identify(request(backend="local"))
    assert result.is_mock and result.model_id == "mock"
    assert result.backend == "local"
    assert all("MOCK" in i.description for i in result.items)


def test_each_identification_gets_its_own_analysis_id(no_ai):
    first, second = orchestrator.identify(request()), orchestrator.identify(request())
    assert first.analysis_id and first.analysis_id != second.analysis_id
    assert all(i.analysis_id == first.analysis_id for i in first.items)


@pytest.mark.parametrize("data", [b"", b"0" * (orchestrator.MAX_IMAGE_BYTES + 1)],
                         ids=["vacia", "mas-de-5-MB"])
def test_rejects_empty_or_oversized_photo_without_retry(no_ai, data):
    error = error_of(orchestrator.identify, request(data))
    assert (error.category, error.retryable) == ("entrada_invalida", False)


def test_accepts_photo_at_exact_size_limit(no_ai):
    assert orchestrator.identify(request(b"0" * orchestrator.MAX_IMAGE_BYTES)).items


def test_rejects_something_that_is_not_a_request():
    assert error_of(orchestrator.identify, {"image_bytes": PNG}).category == "entrada_invalida"


def test_uses_ai_layer_and_overwrites_code_fields(monkeypatch):
    from_model = IdentificationResult(
        items=[DetectedItem(item_id="obj-1", description="Lata", proposed_material=Material.ALUMINIO,
                            visible_evidence="Brillo metálico", analysis_id="inventado")],
        model_id="gemma-4-26b-a4b-it", backend="local", latency_ms=999_999, analysis_id="inventado",
    )
    use_ai(monkeypatch, lambda req: from_model)
    result = orchestrator.identify(request())
    assert not result.is_mock and result.model_id == "gemma-4-26b-a4b-it"
    assert result.backend == "gemini_api"
    assert result.analysis_id != "inventado" and result.items[0].analysis_id == result.analysis_id
    assert result.latency_ms < 999_999


@pytest.mark.parametrize("raised, category", [(TimeoutError(), "timeout"), (RuntimeError("caída"), "api")])
def test_provider_failures_become_retryable_errors(monkeypatch, raised, category):
    def fail(req):
        raise raised
    use_ai(monkeypatch, fail)
    error = error_of(orchestrator.identify, request())
    assert (error.category, error.retryable) == (category, True)


def test_keeps_errors_already_classified_by_ai_layer(monkeypatch):
    classified = AppError(category="formato_invalido", message="JSON inválido", retryable=False)
    def fail(req):
        raise ReciclaClaroError(classified)
    use_ai(monkeypatch, fail)
    assert error_of(orchestrator.identify, request()) == classified


def test_rejects_ai_output_outside_the_contract(monkeypatch):
    use_ai(monkeypatch, lambda req: {"items": []})
    assert error_of(orchestrator.identify, request()).category == "formato_invalido"


def test_reports_photo_without_objects(monkeypatch):
    use_ai(monkeypatch, lambda req: IdentificationResult(items=[], model_id="m", backend="gemini_api",
                                                         latency_ms=0))
    error = error_of(orchestrator.identify, request())
    assert (error.category, error.retryable) == ("sin_datos", True)


def test_missing_dependency_inside_ai_layer_is_not_hidden_as_mock(monkeypatch):
    def broken():
        raise ModuleNotFoundError("No module named 'google'", name="google")
    monkeypatch.setattr(orchestrator.importlib, "import_module", lambda name: broken())
    assert error_of(orchestrator.identify, request()).category == "api"


# --- list_centers y compare ------------------------------------------------------

def test_list_centers_reads_documented_catalog():
    centers = orchestrator.list_centers()
    assert centers and all(c.source_url.startswith("http") and c.rules for c in centers)


def test_compare_builds_plan_for_chosen_center():
    plan = orchestrator.compare([item("obj-1"), item("obj-2")], CENTER_ID)
    assert plan.center.center_id == CENTER_ID
    assert [r.item_id for r in plan.results] == ["obj-1", "obj-2"]
    assert (plan.analysis_id, plan.revision) == ("a1", 0)
    # Un material desconocido nunca se da por aceptado.
    assert all(r.acceptance == "unknown" for r in plan.results)


def test_fingerprint_is_stable_and_changes_when_inputs_change():
    base = orchestrator.compare([item()], CENTER_ID).input_fingerprint
    assert orchestrator.compare([item()], CENTER_ID).input_fingerprint == base
    assert orchestrator.compare([item(material=Material.ALUMINIO)], CENTER_ID).input_fingerprint != base
    assert orchestrator.compare([item(revision=1)], CENTER_ID).input_fingerprint != base
    assert orchestrator.compare([item(analysis_id="otra-foto")], CENTER_ID).input_fingerprint != base
    assert orchestrator._fingerprint([item()], "otro-centro") != base


@pytest.mark.parametrize("items, center_id", [
    ([], CENTER_ID),
    ("obj-1", CENTER_ID),
    ([item()], "centro-inexistente"),
    ([item("obj-1", analysis_id="a1"), item("obj-2", analysis_id="a2")], CENTER_ID),
], ids=["sin-objetos", "no-es-lista", "centro-desconocido", "fotos-distintas"])
def test_compare_rejects_invalid_input_without_retry(items, center_id):
    error = error_of(orchestrator.compare, items, center_id)
    assert (error.category, error.retryable) == ("entrada_invalida", False)
