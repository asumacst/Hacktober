"""Cambiar proveedor o editar el formulario no deja vigente un resultado anterior."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reciclaclaro.contracts import ConfirmedItem, Material  # noqa: E402
from reciclaclaro.ui import state  # noqa: E402

IMG = b"\x89PNG-foto-1"
PET = [ConfirmedItem(item_id="obj-1", material=Material.PET_1)]


def analysed_session():
    ss = state.new_session()
    ss.update(image_bytes=IMG, mime_type="image/png", backend="gemini_api", identification="id",
              confirmed=PET, center_id="c1", plan="p", plan_fp="fp", error="e")
    return ss


def test_changing_backend_clears_analysis_but_keeps_photo():
    ss = analysed_session()
    state.on_backend(ss, "local")
    assert ss["backend"] == "local"
    assert ss["image_bytes"] == IMG and ss["mime_type"] == "image/png"
    for key in state.DOWNSTREAM:
        assert ss[key] is None


def test_same_backend_keeps_everything():
    ss = analysed_session()
    state.on_backend(ss, "gemini_api")
    assert ss["identification"] == "id" and ss["plan"] == "p"


def test_first_backend_on_fresh_session_is_recorded():
    ss = state.new_session()
    state.on_backend(ss, "gemini_api")
    assert ss["backend"] == "gemini_api"


def test_pending_edits_only_after_a_confirmation_that_differs():
    ss = state.new_session()
    assert not state.has_pending_edits(ss, PET)
    ss["confirmed"] = PET
    assert not state.has_pending_edits(ss, [ConfirmedItem(item_id="obj-1", material=Material.PET_1)])
    assert state.has_pending_edits(ss, [ConfirmedItem(item_id="obj-1", material=Material.VIDRIO)])


def test_new_photo_does_not_forget_backend():
    ss = analysed_session()
    state.on_new_photo(ss, b"otra", "image/png")
    assert ss["backend"] == "gemini_api"
