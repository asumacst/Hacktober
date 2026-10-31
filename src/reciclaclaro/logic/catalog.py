"""Carga local del catalogo documentado. No realiza solicitudes de red."""

import json
from pathlib import Path
from urllib.parse import urlparse

from pydantic import TypeAdapter, ValidationError

from reciclaclaro.contracts import AppError, Center, ReciclaClaroError

DEFAULT_CATALOG = Path(__file__).resolve().parents[3] / "data" / "centers.json"


def load_centers(path: str | Path | None = None) -> list[Center]:
    """Leer un array de Center y exigir evidencia e identidades sin duplicados."""
    try:
        payload = json.loads(Path(path or DEFAULT_CATALOG).read_text(encoding="utf-8"))
        centers = TypeAdapter(list[Center]).validate_python(payload)
        if not centers:
            raise ValueError("Catalogo vacio")
        center_ids = set()
        for center in centers:
            if not center.center_id.strip() or center.center_id in center_ids:
                raise ValueError("Identificador de centro vacio o duplicado")
            center_ids.add(center.center_id)
            if urlparse(center.source_url).scheme not in {"http", "https"} or not urlparse(center.source_url).netloc:
                raise ValueError("Centro sin URL web valida")
            if not center.rules:
                raise ValueError("Centro sin reglas")
            rule_ids = set()
            for rule in center.rules:
                if not rule.rule_id or not rule.rule_id.strip() or rule.rule_id in rule_ids:
                    raise ValueError("Identificador de regla ausente o duplicado")
                rule_ids.add(rule.rule_id)
                if not rule.references:
                    raise ValueError("Regla sin referencias")
                if not any(ref.url == rule.source_url and ref.consulted_on == rule.consulted_on
                           for ref in rule.references):
                    raise ValueError("Fuente principal inconsistente con referencias")
                urls = [rule.source_url, *(ref.url for ref in rule.references)]
                if any(urlparse(url).scheme not in {"http", "https"} or not urlparse(url).netloc
                       for url in urls):
                    raise ValueError("Fuente sin URL web valida")
        return centers
    except OSError as exc:
        raise ReciclaClaroError(AppError(
            category="sin_datos", message="No se pudo leer el catalogo local de centros.", retryable=False,
        )) from exc
    except (ValueError, ValidationError) as exc:
        raise ReciclaClaroError(AppError(
            category="formato_invalido", message="El catalogo no tiene reglas y fuentes validas.",
            retryable=False,
        )) from exc
