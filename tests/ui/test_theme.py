"""El estilo inyectado debe sobrevivir al sanitizador de st.html y usar assets existentes."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from reciclaclaro.ui import theme  # noqa: E402


def test_css_has_no_angle_bracket_inside_style():
    # DOMPurify elimina el <style> completo si su contenido parece contener etiquetas.
    css = theme._css()
    body = css.strip().removeprefix("<style>").removesuffix("</style>")
    assert "<" not in body


def test_assets_exist_and_are_svg():
    for name in ("logo.svg", "logo-mark.svg", "topo.svg"):
        assert Path(theme.asset(name)).read_text(encoding="utf-8").lstrip().startswith("<svg")
        assert theme.data_uri(name).startswith("data:image/svg+xml;base64,")
