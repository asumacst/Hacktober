"""Comportamiento de los contratos; ejemplos sinteticos, sin API ni catalogo real."""

from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from reciclaclaro.contracts import (
    Center, CenterRule, ComparisonResult, ConfirmedAttribute, ConfirmedItem,
    DeliveryPlan, DetectedItem, Material, PendingQuestion, SourceReference,
)


def decision(**changes):
    values = dict(item_id="obj-1", center_id="ejemplo", reason="Ejemplo sintetico")
    values.update(changes)
    return ComparisonResult(**values)


def evidence():
    return [{"rule_id": "vidrio-ejemplo", "sources": [{
        "url": "https://example.org/reglas", "entity": "Centro ficticio",
        "consulted_on": "2026-10-31",
    }]}]


@pytest.mark.parametrize("legacy,acceptance", [
    ("aceptado", "accepted"), ("no_admitido", "rejected"), ("pendiente", "unknown"),
])
def test_legacy_decisions_preserve_status_without_assuming_ready(legacy, acceptance):
    result = decision(status=legacy)
    assert result.status == legacy
    assert result.acceptance == acceptance
    assert result.preparation_status == (
        "not_applicable" if acceptance == "rejected" else "unknown"
    )


@pytest.mark.parametrize("acceptance,legacy", [
    ("accepted", "aceptado"), ("rejected", "no_admitido"), ("unknown", "pendiente"),
])
def test_new_decision_exposes_legacy_status(acceptance, legacy):
    assert decision(acceptance=acceptance).status == legacy


def test_accepted_glass_with_food_needs_cleaning():
    result = decision(acceptance="accepted", preparation_status="action_required",
                      preparation_actions=["Retirar restos de comida"], rule_references=evidence())
    assert result.acceptance == "accepted"
    assert result.preparation_status == "action_required"


def test_ready_glass_keeps_rule_and_unknown_publication_date():
    result = decision(acceptance="accepted", preparation_status="ready", rule_references=evidence())
    source = result.rule_references[0].sources[0]
    assert source.consulted_on == date(2026, 10, 31)
    assert source.published_on is None
    assert ComparisonResult.model_validate_json(result.model_dump_json()) == result


def test_unknown_resin_keeps_attribute_question():
    result = decision(acceptance="unknown", missing_data=[PendingQuestion(
        attribute="resin_code", question="Que numero aparece en el simbolo?",
    )])
    assert result.status == "pendiente"
    assert result.preparation_status == "unknown"
    assert result.missing_data[0].attribute == "resin_code"


@pytest.mark.parametrize("changes", [
    {"status": "aceptado", "acceptance": "rejected"},
    {"acceptance": "unknown", "preparation_status": "ready"},
    {"acceptance": "rejected", "preparation_status": "ready"},
    {"acceptance": "rejected", "preparation_actions": ["Limpiar para aceptar"]},
    {"acceptance": "accepted", "preparation_status": "not_applicable"},
    {"acceptance": "accepted", "preparation_status": "action_required"},
    {"acceptance": "accepted", "preparation_status": "ready"},
    {"acceptance": "accepted", "preparation_status": "ready", "rule_references": evidence(),
     "preparation_actions": ["Limpiar"]},
    {"acceptance": "accepted", "preparation_status": "ready", "rule_references": evidence(),
     "missing_data": [{"attribute": "boxed", "question": "Esta en caja?"}]},
    {"acceptance": "unknown", "preparation_status": "action_required", "preparation_actions": ["Limpiar"]},
    {"acceptance": "invented"},
    {"acceptance": []},
    {"status": {}},
    {"acceptance": "unknown", "revision": -1},
])
def test_contradictory_or_incomplete_decisions_are_rejected(changes):
    with pytest.raises(ValidationError):
        decision(**changes)


@pytest.mark.parametrize("values", [
    {"value": True, "source": "unknown"},
    {"value": None, "source": "user_confirmed"},
    {"value": True, "source": "ai"},
])
def test_unconfirmed_proposals_cannot_become_confirmed_attributes(values):
    with pytest.raises(ValidationError):
        ConfirmedAttribute(**values)


def test_false_is_a_valid_confirmed_fact_and_missing_is_unknown():
    dirty = ConfirmedAttribute(value=False, source="user_confirmed")
    assert dirty.value is False
    assert ConfirmedAttribute().value is None


def test_same_polymer_can_have_different_presentations():
    bottle = ConfirmedItem(item_id="bottle", material=Material.PET_1, presentation="botella")
    tray = ConfirmedItem(item_id="tray", material=Material.PET_1, presentation="envase_huevos")
    assert bottle.material == tray.material
    assert bottle.presentation != tray.presentation
    assert bottle.attributes == {}  # No inventar confirmacion por atributo.


def test_confirmed_material_cannot_contradict_material_field():
    with pytest.raises(ValidationError):
        ConfirmedItem(item_id="obj-1", material=Material.VIDRIO, attributes={
            "material": {"value": "PET_1", "source": "user_confirmed"},
        })


def test_legacy_detection_and_rule_still_load():
    detected = DetectedItem(item_id="obj-1", description="Ejemplo", proposed_material="vidrio",
                            visible_evidence="Ejemplo visual")
    rule = CenterRule(material="vidrio", status="aceptado", source_url="https://example.org",
                      consulted_on="2026-10-31")
    assert detected.pending_questions == []
    assert rule.rule_id is None


def test_new_rule_preserves_conditions_and_source_dates():
    rule = CenterRule(material="papel_carton", status="no_admitido", rule_id="carton-grasa",
                      conditions={"greasy": True}, source_url="https://example.org",
                      consulted_on="2026-10-31", references=[SourceReference(
                          url="https://example.org", entity="Ejemplo", consulted_on=date(2026, 10, 31),
                      )])
    assert rule.conditions["greasy"] is True
    assert rule.references[0].updated_on is None


@pytest.mark.parametrize("changes", [
    {"center_id": "otro"}, {"revision": 1}, {"analysis_id": "otra-foto"},
])
def test_plan_rejects_results_from_other_input_context(changes):
    center = Center(center_id="ejemplo", name="Centro ficticio", rules=[],
                    source_url="https://example.org", consulted_on="2026-10-31")
    with pytest.raises(ValidationError):
        DeliveryPlan(center=center, results=[decision(acceptance="unknown", **changes)],
                     generated_at=datetime.now(timezone.utc), input_fingerprint="ejemplo")


def test_legacy_plan_and_result_share_default_context():
    center = Center(center_id="ejemplo", name="Centro ficticio", rules=[],
                    source_url="https://example.org", consulted_on="2026-10-31")
    plan = DeliveryPlan(center=center, results=[decision(status="pendiente")],
                        generated_at=datetime.now(timezone.utc), input_fingerprint="ejemplo")
    assert plan.revision == 0
    assert plan.analysis_id is None
