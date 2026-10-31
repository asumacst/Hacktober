"""Regresiones de calidad del catalogo: un JSON legible no basta para decidir."""

from copy import deepcopy
import json

import pytest

from reciclaclaro.contracts import ConfirmedItem, ReciclaClaroError
from reciclaclaro.logic import compare_item, load_centers
from reciclaclaro.logic.catalog import DEFAULT_CATALOG


@pytest.mark.parametrize("problem", [
    "condition_typo", "extra_rule_field", "extra_source_field", "boolean_as_number",
    "resin_as_text", "inconsistent_resin", "blank_name", "whitespace_id",
    "blank_entity", "bad_source_url", "future_publication", "reversed_dates",
    "duplicate_condition", "duplicate_rule_body", "masked_wrong_type",
])
def test_catalog_rejects_semantically_invalid_records(problem, tmp_path):
    payload = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
    rule = payload[0]["rules"][0]
    if problem == "condition_typo":
        rule["conditons"] = {"clean": True}
    elif problem == "extra_rule_field":
        rule["accept_everything"] = True
    elif problem == "extra_source_field":
        rule["references"][0]["publication_date"] = "2020-01-01"
    elif problem == "boolean_as_number":
        rule["preparation_conditions"]["clean"] = 1
    elif problem == "resin_as_text":
        next(r for r in payload[0]["rules"] if r["material"] == "PET_1")["conditions"]["resin_code"] = "1"
    elif problem == "inconsistent_resin":
        next(r for r in payload[0]["rules"] if r["material"] == "PET_1")["conditions"]["resin_code"] = 2
    elif problem == "blank_name":
        payload[0]["name"] = "  "
    elif problem == "whitespace_id":
        payload[0]["center_id"] += " "
    elif problem == "blank_entity":
        rule["references"][0]["entity"] = "  "
    elif problem == "bad_source_url":
        rule["references"][0]["url"] = "https://not a valid host/"
        rule["source_url"] = rule["references"][0]["url"]
    elif problem == "future_publication":
        rule["references"][0]["published_on"] = "2027-01-01"
    elif problem == "reversed_dates":
        rule["references"][0].update(published_on="2026-09-01", updated_on="2026-01-01")
    elif problem == "duplicate_rule_body":
        duplicate = deepcopy(rule)
        duplicate["rule_id"] += "-duplicate"
        payload[0]["rules"].append(duplicate)
    elif problem == "masked_wrong_type":
        rule["conditions"]["clean"] = 1
    path = tmp_path / "catalog.json"
    text = json.dumps(payload)
    if problem == "duplicate_condition":
        text = text.replace('"clean": true', '"clean": false, "clean": true', 1)
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ReciclaClaroError) as error:
        load_centers(path)
    assert error.value.error.category == "formato_invalido"


def test_direct_rule_with_invalid_reference_cannot_mark_ready():
    center = load_centers()[0]
    for rule in center.rules:
        for ref in rule.references:
            ref.url = "not-a-url"
        rule.source_url = "not-a-url"
    item = ConfirmedItem(
        item_id="glass", material="vidrio", presentation="envase", attributes={
            name: {"value": value, "source": "user_confirmed"}
            for name, value in dict(material="vidrio", presentation="envase", clean=True,
                                    residue_free=True, boxed=True, sorted_by_color=True).items()
        },
    )
    assert compare_item(item, center).acceptance == "unknown"


def test_bom_catalog_loads_from_a_different_working_directory(tmp_path, monkeypatch):
    payload = DEFAULT_CATALOG.read_text(encoding="utf-8")
    path = tmp_path / "catalog.json"
    path.write_text(payload, encoding="utf-8-sig")
    monkeypatch.chdir(tmp_path)
    assert load_centers(path)[0].center_id == load_centers()[0].center_id
