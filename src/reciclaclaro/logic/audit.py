"""Perfil reproducible del catalogo; sin navegacion ni actualizacion de fuentes."""

import argparse
from collections import Counter
import json
from pathlib import Path

from .catalog import DEFAULT_CATALOG, load_centers, text_sha256
from .comparator import _RESIN


def profile_catalog(path: str | Path | None = None) -> dict:
    catalog_path = DEFAULT_CATALOG if path is None else Path(path)
    centers = load_centers(catalog_path)
    rules = [rule for center in centers for rule in center.rules]
    sources = {
        (ref.url, ref.entity, ref.consulted_on.isoformat()): ref
        for rule in rules for ref in rule.references
    }
    requirements = []
    for rule in rules:
        acceptance = {"material", "presentation", *rule.conditions, *rule.required_attributes}
        if rule.material in _RESIN:
            acceptance.add("resin_code")
        requirements.append({
            "rule_id": rule.rule_id, "material": rule.material.value,
            "presentation": rule.presentation, "status": rule.status,
            "acceptance_attributes": sorted(acceptance),
            "preparation_attributes": sorted(rule.preparation_conditions),
        })
    return {
        "scope": "calidad estructural y semantica local; no verifica vigencia en vivo",
        "hash_normalization": "UTF-8 sin BOM; saltos de linea LF",
        "catalog_sha256": text_sha256(catalog_path),
        "centers": len(centers), "rules": len(rules),
        "rules_by_status": dict(sorted(Counter(rule.status for rule in rules).items())),
        "rules_by_material": dict(sorted(Counter(rule.material.value for rule in rules).items())),
        "rules_with_evidence": sum(bool(rule.rule_id and rule.references) for rule in rules),
        "unique_source_records": len(sources),
        "sources_without_publication_date": sum(ref.published_on is None for ref in sources.values()),
        "sources_without_update_date": sum(ref.updated_on is None for ref in sources.values()),
        "unresolved_rule_ids": sorted(rule.rule_id for rule in rules if rule.status == "pendiente"),
        "required_confirmations": sorted(requirements, key=lambda row: row["rule_id"]),
        "warnings": ["Las fechas ausentes no se estiman.",
                     "Una URL valida no demuestra que el centro siga operando ni verifica el contenido de la fuente."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = profile_catalog(args.catalog)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Catalogo valido: {report['centers']} centro(s), {report['rules']} reglas, "
          f"{report['rules_with_evidence']} con evidencia.")
    print(f"Reglas pendientes de aclaracion: {len(report['unresolved_rule_ids'])}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
