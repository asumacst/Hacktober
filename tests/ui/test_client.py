import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from reciclaclaro.contracts import (
    AnalysisRequest, AppError, Center, ConfirmedItem, DeliveryPlan,
    IdentificationResult, Material, ReciclaClaroError,
)
from reciclaclaro.ui import client


@pytest.fixture
def request_image():
    return AnalysisRequest(image_bytes=b"example-image", mime_type="image/png")


@pytest.fixture
def confirmed():
    return [ConfirmedItem(item_id="user-1", material=Material.PET_1)]


@pytest.mark.parametrize("scenario", ["clear_photo", "ambiguous_material", "not_admitted"])
def test_identify_returns_valid_mock_for_each_scenario(monkeypatch, request_image, scenario):
    monkeypatch.setenv("RECICLACLARO_UI_SCENARIO", scenario)
    result = client.identify(request_image)
    assert isinstance(result, IdentificationResult)
    assert result.is_mock is True
    assert result.items
    assert "MOCK" in result.model_id


def test_ambiguous_material_keeps_question(monkeypatch, request_image):
    monkeypatch.setenv("RECICLACLARO_UI_SCENARIO", "ambiguous_material")
    item = client.identify(request_image).items[0]
    assert item.proposed_material == Material.DESCONOCIDO
    assert item.pending_question


def test_api_error_is_typed_and_retryable(monkeypatch, request_image):
    monkeypatch.setenv("RECICLACLARO_UI_SCENARIO", "api_error")
    with pytest.raises(ReciclaClaroError) as exc:
        client.identify(request_image)
    assert isinstance(exc.value.error, AppError)
    assert exc.value.error.category == "api"
    assert exc.value.error.retryable is True
    assert "MOCK" in exc.value.error.message
    # An identification failure must not prevent browsing destinations.
    assert client.list_centers()


def test_centers_are_explicitly_fictional():
    centers = client.list_centers()
    assert centers and all(isinstance(c, Center) for c in centers)
    assert all("MOCK" in c.name for c in centers)
    assert all("example.invalid" in c.source_url for c in centers)
    assert all(c.consulted_on for c in centers)


@pytest.mark.parametrize("material,status", [
    (Material.PET_1, "aceptado"),
    (Material.ALUMINIO, "aceptado"),
    (Material.VIDRIO, "no_admitido"),
    (Material.DESCONOCIDO, "pendiente"),
    (Material.HDPE_2, "pendiente"),
])
def test_compare_replays_fixture_outcomes(material, status):
    center = client.list_centers()[0]
    items = [ConfirmedItem(item_id="my-id", material=material)]
    plan = client.compare(items, center.center_id)
    assert isinstance(plan, DeliveryPlan)
    assert plan.center == center
    assert len(plan.results) == 1
    result = plan.results[0]
    assert result.item_id == "my-id"
    assert result.center_id == center.center_id
    assert result.status == status
    assert "MOCK" in result.reason
    if status == "pendiente":
        assert result.rule_source_url is None
        assert result.consulted_on is None
    else:
        assert result.rule_source_url and result.consulted_on


def test_compare_preserves_order_and_does_not_mutate_input():
    items = [ConfirmedItem(item_id="z", material=Material.VIDRIO),
             ConfirmedItem(item_id="a", material=Material.PET_1)]
    before = [i.model_dump() for i in items]
    plan = client.compare(items, client.list_centers()[0].center_id)
    assert [r.item_id for r in plan.results] == ["z", "a"]
    assert [i.model_dump() for i in items] == before


def test_calls_return_independent_models(request_image):
    first = client.identify(request_image)
    first.items.clear()
    assert client.identify(request_image).items
    center = client.list_centers()[0]
    center.rules.clear()
    assert client.list_centers()[0].rules


def test_fingerprint_is_stable_and_changes_on_confirmed_edit(confirmed):
    center_id = client.list_centers()[0].center_id
    first = client.compare(confirmed, center_id)
    assert first.input_fingerprint == client.compare(confirmed, center_id).input_fingerprint
    edited = [confirmed[0].model_copy(update={"material": Material.VIDRIO, "user_edited": True})]
    updated = client.compare(edited, center_id)
    assert updated.input_fingerprint != first.input_fingerprint
    assert updated.results[0].status == "no_admitido"


@pytest.mark.parametrize("items,center_id", [
    ([], "mock-centro"),
    ([ConfirmedItem(item_id="x", material=Material.PET_1)], "missing-center"),
    ([ConfirmedItem(item_id="x", material=Material.PET_1)] * 2, "mock-centro"),
])
def test_invalid_comparison_is_actionable(items, center_id):
    with pytest.raises(ReciclaClaroError) as exc:
        client.compare(items, center_id)
    assert exc.value.error.category == "entrada_invalida"
    assert exc.value.error.retryable is False


@pytest.mark.parametrize("scenario", ["missing", "../api_error", ""])
def test_unknown_scenario_is_rejected(monkeypatch, request_image, scenario):
    monkeypatch.setenv("RECICLACLARO_UI_SCENARIO", scenario)
    with pytest.raises(ReciclaClaroError) as exc:
        client.identify(request_image)
    assert exc.value.error.category == "entrada_invalida"


def test_unknown_mode_does_not_silently_fall_back(monkeypatch):
    monkeypatch.setenv("RECICLACLARO_UI_MODE", "typo")
    with pytest.raises(ReciclaClaroError) as exc:
        client.list_centers()
    assert exc.value.error.category == "entrada_invalida"


def test_mock_never_imports_orchestrator(monkeypatch, request_image, confirmed):
    def forbidden(*args, **kwargs):
        raise AssertionError("Mock must not import the orchestrator")
    monkeypatch.setattr(client.importlib, "import_module", forbidden)
    result = client.identify(request_image)
    centers = client.list_centers()
    assert result.is_mock
    assert client.compare(confirmed, centers[0].center_id).results


def test_default_mode_is_mock(monkeypatch, request_image):
    monkeypatch.delenv("RECICLACLARO_UI_MODE")
    assert client.identify(request_image).is_mock


def test_local_backend_is_preserved_but_still_mock(request_image):
    request_image.backend = "local"
    result = client.identify(request_image)
    assert result.backend == "local" and result.is_mock


@pytest.mark.parametrize("filename,contents", [
    ("clear_photo.json", "not json"),
    ("clear_photo.json", '{}'),
    ("centers.json", '{}'),
])
def test_invalid_fixture_raises_typed_error(monkeypatch, request_image, filename, contents):
    monkeypatch.setattr(Path, "read_text", lambda *args, **kwargs: contents)
    with pytest.raises(ReciclaClaroError) as exc:
        client.list_centers() if filename == "centers.json" else client.identify(request_image)
    assert exc.value.error.category == "formato_invalido"


def test_missing_fixture_is_actionable(monkeypatch, request_image):
    def missing(*args, **kwargs):
        raise FileNotFoundError("missing example")
    monkeypatch.setattr(Path, "read_text", missing)
    with pytest.raises(ReciclaClaroError) as exc:
        client.identify(request_image)
    assert exc.value.error.category == "sin_datos"


def test_live_delegates_without_network_using_fake_orchestrator(monkeypatch, request_image, confirmed):
    # Capture mock values, then exercise only delegation with an in-memory fake.
    identification = client.identify(request_image).model_copy(update={"is_mock": False})
    centers = client.list_centers()
    plan = client.compare(confirmed, centers[0].center_id)
    fake = SimpleNamespace(identify=Mock(return_value=identification),
                           list_centers=Mock(return_value=centers),
                           compare=Mock(return_value=plan))
    monkeypatch.setitem(sys.modules, "reciclaclaro.orchestrator", fake)
    monkeypatch.setenv("RECICLACLARO_UI_MODE", "live")
    assert client.identify(request_image) == identification
    assert client.list_centers() == centers
    assert client.compare(confirmed, centers[0].center_id) == plan
    fake.identify.assert_called_once_with(request_image)
    fake.list_centers.assert_called_once_with()
    fake.compare.assert_called_once_with(confirmed, centers[0].center_id)


def test_live_preserves_orchestrator_error(monkeypatch, request_image):
    error = ReciclaClaroError(AppError(category="timeout", message="Try again", retryable=True))
    fake = SimpleNamespace(identify=Mock(side_effect=error))
    monkeypatch.setitem(sys.modules, "reciclaclaro.orchestrator", fake)
    monkeypatch.setenv("RECICLACLARO_UI_MODE", "live")
    with pytest.raises(ReciclaClaroError) as exc:
        client.identify(request_image)
    assert exc.value is error


def test_live_without_orchestrator_never_uses_mock(monkeypatch, request_image):
    monkeypatch.setitem(sys.modules, "reciclaclaro.orchestrator", None)
    monkeypatch.setenv("RECICLACLARO_UI_MODE", "live")
    with pytest.raises(ReciclaClaroError) as exc:
        client.identify(request_image)
    assert exc.value.error.category == "sin_datos"


def test_fixture_json_files_are_readable():
    files = list((Path(client.__file__).parent / "fixtures").glob("*.json"))
    assert len(files) >= 5
    for file in files:
        assert json.loads(file.read_text(encoding="utf-8"))


@pytest.mark.parametrize("contents", ['{}', '[]', '{"desconocido": {}}'])
def test_invalid_comparison_fixture_raises_typed_error(monkeypatch, confirmed, contents):
    original = Path.read_text

    def read(path, *args, **kwargs):
        return contents if path.name == "comparisons.json" else original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read)
    with pytest.raises(ReciclaClaroError) as exc:
        client.compare(confirmed, "mock-centro")
    assert exc.value.error.category == "formato_invalido"


def test_live_invalid_response_is_not_rendered_as_valid(monkeypatch, request_image):
    fake = SimpleNamespace(identify=Mock(return_value={"items": "invalid"}))
    monkeypatch.setitem(sys.modules, "reciclaclaro.orchestrator", fake)
    monkeypatch.setenv("RECICLACLARO_UI_MODE", "live")
    with pytest.raises(ReciclaClaroError) as exc:
        client.identify(request_image)
    assert exc.value.error.category == "formato_invalido"
