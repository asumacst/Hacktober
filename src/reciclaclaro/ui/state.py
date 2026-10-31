"""Estado de la interfaz: claves de sesión e invalidación del plan.

Funciones puras sobre un MutableMapping para poder probarlas sin Streamlit
(st.session_state se comporta como un dict).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import MutableMapping

from reciclaclaro.contracts import ConfirmedItem

KEYS = (
    "image_bytes", "mime_type", "identification", "confirmed",
    "center_id", "plan", "plan_fp", "error",
)
DOWNSTREAM = ("identification", "confirmed", "center_id", "plan", "plan_fp", "error")


def new_session() -> dict:
    return {key: None for key in KEYS}


def init(ss: MutableMapping) -> None:
    for key in KEYS:
        ss.setdefault(key, None)


def fingerprint(image_bytes: bytes, items: list[ConfirmedItem], center_id: str | None) -> str:
    """Huella de las entradas del plan: cambia si cambia la foto, un material o el centro."""
    h = hashlib.sha256(image_bytes)
    payload = sorted((i.model_dump(mode="json") for i in items), key=lambda d: d["item_id"])
    h.update(json.dumps(payload, sort_keys=True).encode())
    h.update((center_id or "").encode())
    return h.hexdigest()


def on_new_photo(ss: MutableMapping, image_bytes: bytes, mime_type: str) -> None:
    ss["image_bytes"] = image_bytes
    ss["mime_type"] = mime_type
    for key in DOWNSTREAM:
        ss[key] = None


def plan_is_current(ss: MutableMapping, current_fp: str) -> bool:
    return ss.get("plan") is not None and ss.get("plan_fp") == current_fp
