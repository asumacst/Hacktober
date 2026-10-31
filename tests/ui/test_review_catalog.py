"""Las confirmaciones del formulario bastan para que el comparador real decida."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reciclaclaro.contracts import DetectedItem, Material  # noqa: E402
from reciclaclaro.logic import compare_item, load_centers  # noqa: E402
from reciclaclaro.ui.components import UNKNOWN, _confirmed_item, catalog_fields  # noqa: E402

CENTERS = load_centers()
CENTER = CENTERS[0]


def detected(material, presentation=None):
    return DetectedItem(item_id="obj-1", description="Objeto", proposed_material=material,
                        proposed_presentation=presentation, visible_evidence="Foto")


def row(material, presentation=UNKNOWN, resin=None, clean=UNKNOWN, confirm=True, **checks):
    return {"item_id": "obj-1", "Material": material.value, "Presentación": presentation,
            "Símbolo": resin, "¿Limpio?": clean, "Confirmo": confirm, "checks": checks}


def test_catalog_fields_ask_only_what_the_material_rules_use():
    presentations, checks, needs_resin = catalog_fields(CENTERS, Material.PAPEL_CARTON)
    assert presentations == ["caja", "caja_desarmada"]
    assert {"corrugated", "wet", "greasy", "painted", "clean", "residue_free"} <= set(checks)
    assert "sorted_by_color" not in checks
    assert needs_resin is False
    presentations, checks, needs_resin = catalog_fields(CENTERS, Material.VIDRIO)
    assert "envase" in presentations and "espejo" in presentations
    assert {"boxed", "sorted_by_color"} <= set(checks)


def test_material_without_rules_still_asks_resin_for_plastics_and_unknown():
    assert catalog_fields([], Material.PP_5) == ([], [], True)
    assert catalog_fields([], Material.ALUMINIO) == ([], [], False)
    assert catalog_fields(CENTERS, Material.DESCONOCIDO)[2] is True


def test_presentation_is_sent_only_when_confirmed():
    item = _confirmed_item(row(Material.PET_1, "botella", confirm=False), detected(Material.PET_1), None)
    assert item.presentation is None
    assert "presentation" not in item.attributes
    item = _confirmed_item(row(Material.PET_1, "botella"), detected(Material.PET_1), None)
    assert item.presentation == "botella"
    assert item.attributes["presentation"].value == "botella"


def test_unknown_answers_stay_pending():
    item = _confirmed_item(row(Material.VIDRIO, "envase", boxed=UNKNOWN), detected(Material.VIDRIO), None)
    assert "boxed" not in item.attributes
    result = compare_item(item, CENTER)
    assert result.acceptance == "accepted"
    assert result.preparation_status == "unknown"
    assert {q.attribute for q in result.missing_data} >= {"boxed", "clean"}


def test_full_pet_confirmation_is_ready():
    item = _confirmed_item(row(Material.PET_1, "botella", resin=1.0, clean="Sí",
                               residue_free="Sí", sorted_by_color="Sí"), detected(Material.PET_1), None)
    result = compare_item(item, CENTER)
    assert result.acceptance == "accepted"
    assert result.preparation_status == "ready"


def test_full_glass_confirmation_is_ready():
    item = _confirmed_item(row(Material.VIDRIO, "envase", clean="Sí", residue_free="Sí",
                               boxed="Sí", sorted_by_color="Sí"), detected(Material.VIDRIO), None)
    assert compare_item(item, CENTER).preparation_status == "ready"


def test_wet_cardboard_is_rejected():
    item = _confirmed_item(row(Material.PAPEL_CARTON, "caja", corrugated="Sí", wet="Sí"),
                           detected(Material.PAPEL_CARTON), None)
    assert compare_item(item, CENTER).acceptance == "rejected"


def test_clean_dismantled_cardboard_is_ready():
    item = _confirmed_item(row(Material.PAPEL_CARTON, "caja_desarmada", clean="Sí", corrugated="Sí",
                               wet="No", greasy="No", painted="No", residue_free="Sí"),
                           detected(Material.PAPEL_CARTON), None)
    assert compare_item(item, CENTER).preparation_status == "ready"
