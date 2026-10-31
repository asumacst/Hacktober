"""Decisiones esperadas y errores de datos, sin acceder a la red."""

from copy import deepcopy
from itertools import product
import json

import pytest

from reciclaclaro.contracts import ConfirmedItem, ReciclaClaroError
from reciclaclaro.logic import compare_item, compare_items, load_centers
from reciclaclaro.logic.catalog import DEFAULT_CATALOG
from reciclaclaro.logic.examples import CASES_PATH, run_examples

CASES = json.loads(CASES_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def center():
    return load_centers()[0]


def sample(case_id="vidrio-listo"):
    return ConfirmedItem.model_validate(next(case["item"] for case in CASES if case["case_id"] == case_id))


@pytest.mark.parametrize("case", CASES, ids=[case["case_id"] for case in CASES])
def test_documented_cases(case, center):
    result = compare_item(ConfirmedItem.model_validate(case["item"]), center)
    assert result.acceptance == case["expected"]["acceptance"]
    assert result.preparation_status == case["expected"]["preparation_status"]
    assert result.item_id == case["item"]["item_id"]
    if result.acceptance != "unknown":
        assert result.rule_references
        assert result.consulted_on is not None


def test_catalog_has_three_categories_and_unique_rule_ids(center):
    assert {rule.material.value for rule in center.rules} == {"PET_1", "HDPE_2", "PP_5", "vidrio", "papel_carton"}
    assert len({rule.rule_id for rule in center.rules}) == len(center.rules)
    assert all(ref.published_on is None for rule in center.rules for ref in rule.references)


def test_raw_ai_or_legacy_details_do_not_confirm_facts(center):
    item = ConfirmedItem(item_id="obj", material="PET_1", details="botella PET simbolo 1", user_edited=True)
    result = compare_item(item, center)
    assert result.acceptance == "unknown"
    assert {question.attribute for question in result.missing_data} == {"material", "presentation"}


def test_unknown_material_is_not_a_rejection(center):
    assert compare_item(sample("material-desconocido"), center).status == "pendiente"


@pytest.mark.parametrize("value", [True, "1", 2, 0, 8])
def test_wrong_resin_type_or_conflict_never_accepts(value, center):
    payload = sample("pet-botella-lista").model_dump()
    payload["attributes"]["resin_code"] = {"value": value, "source": "user_confirmed"}
    result = compare_item(ConfirmedItem.model_validate(payload), center)
    assert result.acceptance == "unknown"
    assert result.missing_data[0].attribute == "resin_code"


def test_unlisted_presentation_does_not_inherit_material_acceptance(center):
    payload = sample().model_dump()
    payload["presentation"] = "objeto_no_documentado"
    payload["attributes"]["presentation"]["value"] = "objeto_no_documentado"
    result = compare_item(ConfirmedItem.model_validate(payload), center)
    assert result.acceptance == "unknown"


@pytest.mark.parametrize("attribute", ["wet", "greasy", "painted"])
def test_cardboard_exclusion_overrides_preparation(attribute, center):
    payload = sample("carton-listo").model_dump()
    payload["attributes"][attribute]["value"] = True
    result = compare_item(ConfirmedItem.model_validate(payload), center)
    assert result.acceptance == "rejected"
    assert result.preparation_actions == []


def test_unresolved_cardboard_exclusion_blocks_acceptance(center):
    payload = sample("carton-listo").model_dump()
    del payload["attributes"]["greasy"]
    result = compare_item(ConfirmedItem.model_validate(payload), center)
    assert result.acceptance == "unknown"
    assert "greasy" in {question.attribute for question in result.missing_data}


def test_dirty_glass_and_missing_box_show_actions_and_questions(center):
    payload = sample("vidrio-con-comida").model_dump()
    del payload["attributes"]["boxed"]
    result = compare_item(ConfirmedItem.model_validate(payload), center)
    assert result.preparation_status == "action_required"
    assert result.preparation_actions
    assert "boxed" in {question.attribute for question in result.missing_data}


@pytest.mark.parametrize("value", ["true", 1])
def test_boolean_strings_or_numbers_cannot_make_object_ready(value, center):
    payload = sample().model_dump()
    payload["attributes"]["clean"]["value"] = value
    result = compare_item(ConfirmedItem.model_validate(payload), center)
    assert result.preparation_status == "unknown"


def test_facts_are_reevaluated_after_user_correction(center):
    dirty = sample("vidrio-con-comida")
    before = dirty.model_dump_json()
    initial = compare_item(dirty, center)
    payload = dirty.model_dump()
    payload["revision"] = 1
    for name in ["clean", "residue_free"]:
        payload["attributes"][name]["value"] = True
    updated = compare_item(ConfirmedItem.model_validate(payload), center)
    assert initial.preparation_status == "action_required"
    assert updated.preparation_status == "ready"
    assert updated.revision == 1
    assert dirty.model_dump_json() == before


def test_center_change_recomputes_and_keeps_new_identity(center):
    other = center.model_copy(deep=True, update={"center_id": "centro-sintetico-sin-reglas", "rules": []})
    assert compare_item(sample(), center).acceptance == "accepted"
    result = compare_item(sample(), other)
    assert result.center_id == other.center_id
    assert result.acceptance == "unknown"


def test_list_returns_ordered_results_and_empty_list(center):
    assert compare_items([], center) == []
    results = compare_items([sample(), sample("espejo")], center)
    assert [result.item_id for result in results] == ["vidrio-listo", "espejo"]


@pytest.mark.parametrize("change", [{"revision": 1}, {"analysis_id": "otra-foto"}, {"item_id": "vidrio-listo"}])
def test_batch_rejects_mixed_context_or_duplicate_ids(change, center):
    second = sample("espejo").model_copy(update=change)
    with pytest.raises(ReciclaClaroError) as error:
        compare_items([sample(), second], center)
    assert error.value.error.category == "entrada_invalida"


def test_invalid_input_has_app_error(center):
    with pytest.raises(ReciclaClaroError):
        compare_items([{}], center)
    with pytest.raises(ReciclaClaroError):
        compare_item({}, center)
    with pytest.raises(ReciclaClaroError):
        compare_items([], {})


@pytest.mark.parametrize("case_id,status", [("vidrio-listo", "aceptado"), ("espejo", "no_admitido")])
def test_direct_center_without_evidence_does_not_decide(case_id, status, center):
    incomplete = center.model_copy(deep=True)
    for rule in incomplete.rules:
        if rule.status == status:
            rule.references = []
    assert compare_item(sample(case_id), incomplete).acceptance == "unknown"


def test_empty_catalog_fails_closed_for_single_object(center):
    center.rules = []
    assert compare_item(sample(), center).acceptance == "unknown"


def test_multiple_comparisons_do_not_share_pending_lists(center):
    first = compare_item(sample("pet-sin-codigo"), center)
    second = compare_item(sample("pet-sin-codigo"), center)
    first.missing_data.clear()
    assert second.missing_data


def test_rule_without_preparation_information_cannot_assume_ready(center):
    incomplete = center.model_copy(deep=True)
    for rule in incomplete.rules:
        if rule.status == "aceptado":
            rule.preparation_conditions = {}
            rule.preparation = None
    result = compare_item(sample(), incomplete)
    assert result.acceptance == "accepted"
    assert result.preparation_status == "unknown"


def test_unstructured_instruction_remains_an_action_until_verifiable(center):
    incomplete = center.model_copy(deep=True)
    for rule in incomplete.rules:
        if rule.status == "aceptado":
            rule.preparation_conditions = {}
    result = compare_item(sample(), incomplete)
    assert result.preparation_status == "action_required"


def test_glass_readiness_requires_all_four_confirmations(center):
    # 81 combinaciones: un dato desconocido nunca cuenta como un si.
    names = ["clean", "residue_free", "boxed", "sorted_by_color"]
    for values in product((True, False, None), repeat=4):
        payload = sample().model_dump()
        for name, value in zip(names, values):
            payload["attributes"][name] = {
                "value": value, "source": "unknown" if value is None else "user_confirmed",
            }
        result = compare_item(ConfirmedItem.model_validate(payload), center)
        assert result.acceptance == "accepted", values
        assert (result.preparation_status == "ready") == all(value is True for value in values), values
        assert {q.attribute for q in result.missing_data} == {
            name for name, value in zip(names, values) if value is None
        }, values
        if any(value is False for value in values):
            assert result.preparation_status == "action_required", values


def test_carton_exclusions_and_unknowns_for_all_27_combinations(center):
    names = ["wet", "greasy", "painted"]
    for values in product((True, False, None), repeat=3):
        payload = sample("carton-listo").model_dump()
        for name, value in zip(names, values):
            payload["attributes"][name] = {
                "value": value, "source": "unknown" if value is None else "user_confirmed",
            }
        result = compare_item(ConfirmedItem.model_validate(payload), center)
        if any(value is True for value in values):
            assert result.acceptance == "rejected", values
            assert not result.preparation_actions, values
        elif any(value is None for value in values):
            assert result.acceptance == "unknown", values
        else:
            assert result.acceptance == "accepted", values


@pytest.mark.parametrize("kind", ["empty", "broken_json", "wrong_root", "duplicate_center", "duplicate_rule", "no_source", "no_rule_id", "bad_url"])
def test_invalid_catalog_fails_explicitly(kind, tmp_path):
    data = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
    if kind == "empty":
        data = []
    elif kind == "wrong_root":
        data = {"centers": data}
    elif kind == "duplicate_center":
        data.append(deepcopy(data[0]))
    elif kind == "duplicate_rule":
        data[0]["rules"].append(deepcopy(data[0]["rules"][0]))
    elif kind == "no_source":
        data[0]["rules"][0]["references"] = []
    elif kind == "no_rule_id":
        data[0]["rules"][0]["rule_id"] = None
    elif kind == "bad_url":
        data[0]["rules"][0]["references"][0]["url"] = "sin-url"
    path = tmp_path / "catalog.json"
    path.write_text("{" if kind == "broken_json" else json.dumps(data), encoding="utf-8")
    with pytest.raises(ReciclaClaroError) as error:
        load_centers(path)
    assert error.value.error.category == "formato_invalido"


def test_missing_catalog_is_not_reported_as_rejection(tmp_path):
    with pytest.raises(ReciclaClaroError) as error:
        load_centers(tmp_path / "missing.json")
    assert error.value.error.category == "sin_datos"


def test_shared_outputs_match_expected_results():
    outputs = run_examples()
    assert len(outputs) == len(CASES)
    assert all(output["is_mock"] and output["matches_expected"] for output in outputs)
