"""Identidad visual de la interfaz: tokens «Canal y selva», logotipo y estilos.

Solo presentación. Los colores base también están en .streamlit/config.toml;
aquí van los detalles que el tema nativo de Streamlit no cubre.
"""

from __future__ import annotations

import base64
from functools import cache
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent / "assets"

TOKENS = {
    "primary": "#0B5D55", "secondary": "#2F8F5B", "bg": "#F6F1E7", "surface": "#FFFFFF",
    "accent": "#E9A23B", "ink": "#17302C", "muted": "#5B6E69", "line": "#DDD4C2",
    "ok": "#1E7A46", "no": "#B3261E", "pending": "#9A6700", "info": "#0B5D55",
}


def asset(name: str) -> str:
    return str(ASSETS / name)


@cache
def data_uri(name: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def _css() -> str:
    t = TOKENS
    root = "\n".join(f"  --rc-{k}: {v};" for k, v in t.items())
    return f"""
<style>
:root {{
{root}
  --rc-radius: 14px;
  --rc-shadow: 0 1px 2px rgba(23,48,44,.06), 0 8px 24px rgba(23,48,44,.06);
}}

/* Fondo arena con curvas de nivel tenues */
[data-testid="stApp"] {{
  background-color: var(--rc-bg);
  background-image: url("{data_uri('topo.svg')}");
  background-size: 400px 400px;
}}
[data-testid="stHeader"] {{
  background: rgba(246,241,231,.82); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px);
}}
[data-testid="stMainBlockContainer"] {{ padding-top: 2.5rem; padding-bottom: 4rem; }}

/* Encabezado */
.rc-hero {{
  display: flex; align-items: center; gap: 1.1rem;
  padding: 1.4rem 1.6rem; border-radius: 20px; color: #fff;
  background: linear-gradient(120deg, var(--rc-primary) 0%, #0E6B5C 55%, var(--rc-secondary) 100%);
  box-shadow: var(--rc-shadow);
  animation: rc-rise .28s ease-out both;
}}
.rc-hero img {{ width: 64px; height: 64px; flex: none; border-radius: 16px;
  box-shadow: 0 0 0 2px rgba(255,255,255,.25); }}
.rc-hero h1 {{ margin: 0; padding: 0; font-size: 2.1rem; line-height: 1.1; color: #fff;
  letter-spacing: -.02em; }}
.rc-hero h1 span {{ color: #CDEBD9; }}
.rc-hero p {{ margin: .35rem 0 0; color: rgba(255,255,255,.88); font-size: .98rem; }}

/* Indicador de pasos */
.rc-steps {{ display: flex; gap: .5rem; list-style: none; margin: 1rem 0 .25rem !important;
  padding: 0 !important; }}
.rc-steps li {{ margin: 0 !important; }}
.rc-steps li {{
  flex: 1; display: flex; align-items: center; gap: .45rem; min-width: 0;
  padding: .5rem .7rem; border-radius: 999px; font-size: .85rem; font-weight: 600;
  color: var(--rc-muted); background: rgba(255,255,255,.7); border: 1px solid var(--rc-line);
  transition: background-color .2s ease, color .2s ease, border-color .2s ease;
}}
.rc-steps li b {{
  display: inline-grid; place-items: center; width: 1.45rem; height: 1.45rem; flex: none;
  border-radius: 50%; font-size: .75rem; background: var(--rc-line); color: var(--rc-ink);
}}
.rc-steps li span {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.rc-steps li.done {{ color: var(--rc-ok); border-color: #BFDCCB; background: #EEF7F1; }}
.rc-steps li.done b {{ background: var(--rc-ok); color: #fff; }}
.rc-steps li.now {{ color: var(--rc-ink); border-color: var(--rc-accent); background: #FFF6E6;
  box-shadow: 0 0 0 3px rgba(233,162,59,.18); }}
.rc-steps li.now b {{ background: var(--rc-accent); color: var(--rc-ink); }}

/* Títulos de sección */
[data-testid="stMain"] h3 {{ margin-top: 1.6rem; letter-spacing: -.01em; }}

/* Tarjetas: contenedores con borde y clave rc-*; st.container(key=...) añade la clase st-key-[clave] */
[data-testid="stVerticalBlock"][class*="st-key-rc-"] {{
  background: var(--rc-surface);
  border-color: var(--rc-line) !important;
  border-radius: var(--rc-radius) !important;
  box-shadow: var(--rc-shadow);
  animation: rc-rise .22s ease-out both;
}}
[data-testid="stVerticalBlock"][class*="st-key-rc-result-"] {{ border-left-width: 6px !important; }}
[data-testid="stVerticalBlock"][class*="st-key-rc-result-ok"] {{ border-left-color: var(--rc-ok) !important; }}
[data-testid="stVerticalBlock"][class*="st-key-rc-result-prep"] {{ border-left-color: var(--rc-info) !important; }}
[data-testid="stVerticalBlock"][class*="st-key-rc-result-no"] {{ border-left-color: var(--rc-no) !important; }}
[data-testid="stVerticalBlock"][class*="st-key-rc-result-pending"] {{
  border-left-color: var(--rc-pending) !important; }}

/* Métricas del plan */
[data-testid="stMetric"] {{
  background: var(--rc-surface); border: 1px solid var(--rc-line); border-radius: var(--rc-radius);
  padding: .8rem 1rem; box-shadow: var(--rc-shadow);
}}
[data-testid="stMetricValue"] {{ font-family: "Plus Jakarta Sans", sans-serif; font-weight: 800; }}

/* Carga de la foto */
[data-testid="stFileUploaderDropzone"] {{
  background: var(--rc-surface); border: 2px dashed #BFD3CB; border-radius: var(--rc-radius);
  transition: border-color .2s ease, background-color .2s ease;
}}
[data-testid="stFileUploaderDropzone"]:hover {{ border-color: var(--rc-primary); background: #F2F8F6; }}
[data-testid="stImage"] img {{ border-radius: var(--rc-radius); box-shadow: var(--rc-shadow); }}

/* Botones */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] {{
  min-height: 44px; padding-inline: 1.2rem; font-weight: 600;
  transition: transform .12s ease, box-shadow .2s ease, background-color .2s ease;
}}
[data-testid="stBaseButton-primary"] {{
  background: var(--rc-primary) !important; border-color: var(--rc-primary) !important; color: #fff !important;
}}
[data-testid="stBaseButton-primary"]:hover:not(:disabled) {{
  background: #0E6B5C !important; border-color: #0E6B5C !important;
  transform: translateY(-1px); box-shadow: 0 6px 16px rgba(11,93,85,.25);
}}
[data-testid="stBaseButton-primary"]:active:not(:disabled) {{ background: #094C46 !important; transform: none; }}
[data-testid="stBaseButton-primary"]:disabled {{
  background: #C9D9D4 !important; border-color: #C9D9D4 !important; color: #3D5550 !important;
}}
button:focus-visible, [role="radio"]:focus-visible, input:focus-visible, [tabindex]:focus-visible {{
  outline: 3px solid var(--rc-accent) !important; outline-offset: 2px;
}}

/* Avisos */
[data-testid="stAlert"] {{ border-radius: 12px; }}

/* Barra lateral */
[data-testid="stSidebar"] {{ border-right: 1px solid var(--rc-line); }}

/* Pie */
.rc-footer {{
  margin-top: 2.5rem; padding-top: 1rem; border-top: 1px solid var(--rc-line);
  display: flex; flex-wrap: wrap; gap: .4rem .9rem; align-items: center;
  font-size: .82rem; color: var(--rc-muted);
}}
.rc-footer code {{ background: #EAE3D4; color: var(--rc-ink); padding: .05rem .4rem; border-radius: 6px; }}
.rc-footer .rc-mock {{ background: #FFF6E6; color: #7A5200; border: 1px solid #F1D29C;
  padding: .05rem .5rem; border-radius: 999px; font-weight: 600; }}

@keyframes rc-rise {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}

@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 4.25rem 1rem 3rem; }}
  .rc-hero {{ padding: 1.1rem; gap: .8rem; border-radius: 16px; }}
  .rc-hero img {{ width: 48px; height: 48px; border-radius: 12px; }}
  .rc-hero h1 {{ font-size: 1.55rem; }}
  .rc-hero p {{ font-size: .9rem; }}
  .rc-steps {{ gap: .3rem; }}
  .rc-steps li {{ padding: .45rem; justify-content: center; }}
  .rc-steps li span {{ display: none; }}
  .rc-steps li.now span {{ display: inline; }}
}}

@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
</style>
"""


def apply() -> None:
    """Inyecta los estilos. Llamar una vez por ejecución, después de set_page_config.

    Ojo: el sanitizador de st.html descarta el <style> entero si su texto contiene «<».
    """
    st.html(_css())
