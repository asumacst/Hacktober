import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reciclaclaro.contracts import ConfirmedItem, Material  # noqa: E402
from reciclaclaro.ui import state  # noqa: E402

IMG = b"\x89PNG-foto-1"
ITEMS = [ConfirmedItem(item_id="obj-1", material=Material.PET_1)]


def test_fingerprint_is_stable_for_same_inputs():
    assert state.fingerprint(IMG, ITEMS, "c1") == state.fingerprint(IMG, list(ITEMS), "c1")


def test_fingerprint_ignores_item_order():
    a = ConfirmedItem(item_id="a", material=Material.VIDRIO)
    b = ConfirmedItem(item_id="b", material=Material.ALUMINIO)
    assert state.fingerprint(IMG, [a, b], "c1") == state.fingerprint(IMG, [b, a], "c1")


def test_fingerprint_changes_with_photo_material_or_center():
    base = state.fingerprint(IMG, ITEMS, "c1")
    assert state.fingerprint(b"otra-foto", ITEMS, "c1") != base
    assert state.fingerprint(IMG, [ConfirmedItem(item_id="obj-1", material=Material.HDPE_2)], "c1") != base
    assert state.fingerprint(IMG, ITEMS, "c2") != base


def test_new_photo_clears_everything_downstream():
    ss = state.new_session()
    ss.update(identification="x", confirmed="y", center_id="c1", plan="p", plan_fp="fp", error="e")
    state.on_new_photo(ss, IMG, "image/png")
    assert ss["image_bytes"] == IMG
    for key in ("identification", "confirmed", "center_id", "plan", "plan_fp", "error"):
        assert ss[key] is None


def test_plan_is_current_only_when_fingerprint_matches():
    ss = state.new_session()
    assert not state.plan_is_current(ss, "fp")
    ss.update(plan="p", plan_fp="fp")
    assert state.plan_is_current(ss, "fp")
    assert not state.plan_is_current(ss, "otro")
