"""Carga local del catalogo documentado. No realiza solicitudes de red."""

import json
import hashlib
from pathlib import Path
from pydantic import HttpUrl, TypeAdapter, ValidationError

from reciclaclaro.contracts import AppError, Center, CenterRule, Material, ReciclaClaroError, SourceReference

DEFAULT_CATALOG = Path(__file__).resolve().parents[3] / "data" / "centers.json"
_BOOL_ATTRIBUTES = {
    "clean", "residue_free", "corrugated", "wet", "greasy", "painted", "boxed", "sorted_by_color",
}
_RESIN = {Material.PET_1: 1, Material.HDPE_2: 2, Material.PP_5: 5}


def text_sha256(path: Path) -> str:
    """Huella independiente de CRLF/LF y BOM para archivos de texto del repo."""
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode("utf-8")).hexdigest()


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Clave JSON duplicada")
        result[key] = value
    return result


def _check_fields(record, model):
    if isinstance(record, dict) and set(record) - model.model_fields.keys():
        raise ValueError("Campo de catalogo no reconocido")


def _check_raw_fields(payload):
    # Los contratos compartidos aceptan campos extra; el catalogo no debe perder
    # silenciosamente condiciones por un error de escritura.
    if not isinstance(payload, list):
        return
    for center in payload:
        _check_fields(center, Center)
        if not isinstance(center, dict) or not isinstance(center.get("rules"), list):
            continue
        for rule in center["rules"]:
            _check_fields(rule, CenterRule)
            if isinstance(rule, dict) and isinstance(rule.get("references"), list):
                for ref in rule["references"]:
                    _check_fields(ref, SourceReference)


def _valid_url(url):
    if not url or any(character.isspace() for character in url):
        return False
    try:
        parsed = TypeAdapter(HttpUrl).validate_python(url)
    except (ValueError, TypeError):
        return False
    return parsed.username is None and parsed.password is None


def _valid_reference(ref):
    return (
        bool(ref.entity.strip()) and _valid_url(ref.url)
        and (ref.published_on is None or ref.published_on <= ref.consulted_on)
        and (ref.updated_on is None or ref.updated_on <= ref.consulted_on)
        and (ref.published_on is None or ref.updated_on is None or ref.published_on <= ref.updated_on)
    )


def has_rule_evidence(rule: CenterRule) -> bool:
    """Exigir referencias coherentes incluso al recibir un Center directamente."""
    return bool(
        rule.rule_id and rule.rule_id.strip() == rule.rule_id and _valid_url(rule.source_url)
        and rule.references and all(_valid_reference(ref) for ref in rule.references)
        and any(ref.url == rule.source_url and ref.consulted_on == rule.consulted_on
                for ref in rule.references)
    )


def _check_condition_types(rule):
    for name, value in [*rule.conditions.items(), *rule.preparation_conditions.items()]:
        if name in _BOOL_ATTRIBUTES:
            if type(value) is not bool:
                raise ValueError("Una condicion booleana necesita true o false")
        elif name == "resin_code":
            if type(value) is not int or value not in range(1, 8):
                raise ValueError("Codigo de resina invalido")
            if rule.material in _RESIN and value != _RESIN[rule.material]:
                raise ValueError("El codigo de resina contradice el material de la regla")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError("Una condicion textual necesita texto no vacio")
    if len(set(rule.required_attributes)) != len(rule.required_attributes):
        raise ValueError("Atributo requerido duplicado")


def load_centers(path: str | Path | None = None) -> list[Center]:
    """Leer un array de Center y exigir evidencia e identidades sin duplicados."""
    try:
        catalog_path = DEFAULT_CATALOG if path is None else Path(path)
        payload = json.loads(catalog_path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_keys)
        _check_raw_fields(payload)
        centers = TypeAdapter(list[Center]).validate_python(payload)
        if not centers:
            raise ValueError("Catalogo vacio")
        center_ids = set()
        for center in centers:
            if (not center.center_id.strip() or center.center_id.strip() != center.center_id
                    or center.center_id in center_ids or not center.name.strip()):
                raise ValueError("Identificador de centro vacio o duplicado")
            center_ids.add(center.center_id)
            if not _valid_url(center.source_url):
                raise ValueError("Centro sin URL web valida")
            if not center.rules:
                raise ValueError("Centro sin reglas")
            rule_ids = set()
            signatures = set()
            for rule in center.rules:
                if not rule.rule_id or not rule.rule_id.strip() or rule.rule_id in rule_ids:
                    raise ValueError("Identificador de regla ausente o duplicado")
                rule_ids.add(rule.rule_id)
                if not has_rule_evidence(rule):
                    raise ValueError("Regla sin referencias y fechas coherentes")
                _check_condition_types(rule)
                body = rule.model_dump(mode="json", exclude={"rule_id", "references", "source_url", "consulted_on"})
                signature = json.dumps(body, sort_keys=True)
                if signature in signatures:
                    raise ValueError("Regla semantica duplicada; consolidar sus fuentes")
                signatures.add(signature)
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
