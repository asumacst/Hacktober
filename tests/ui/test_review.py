import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reciclaclaro.contracts import DetectedItem, Material  # noqa: E402
from reciclaclaro.ui.components import UNKNOWN, _confirmed_item  # noqa: E402

ORIGINAL = DetectedItem(item_id="obj-1", description="Botella", proposed_material=Material.PET_1,
                        visible_evidence="Símbolo visible")


def row(**changes):
    values = {"item_id": "obj-1", "Material": "PET_1", "Confirmo": False, "Símbolo": None, "¿Limpio?": UNKNOWN}
    values.update(changes)
    return values


def test_gemma_proposal_is_not_copied_as_confirmed():
    item = _confirmed_item(row(), ORIGINAL, "foto-1")
    assert item.material == Material.PET_1
    assert item.attributes == {}
    assert item.user_edited is False
    assert item.analysis_id == "foto-1"


def test_only_what_the_person_marks_becomes_confirmed():
    item = _confirmed_item(row(Confirmo=True, **{"Símbolo": 1.0, "¿Limpio?": "No"}), ORIGINAL, None)
    assert item.attributes["material"].value == "PET_1"
    assert item.attributes["resin_code"].value == 1
    assert item.attributes["clean"].value is False
    assert all(a.source == "user_confirmed" for a in item.attributes.values())


def test_correcting_the_material_marks_the_item_as_edited():
    item = _confirmed_item(row(Material="vidrio", Confirmo=True), ORIGINAL, None)
    assert item.material == Material.VIDRIO
    assert item.attributes["material"].value == "vidrio"
    assert item.user_edited is True
