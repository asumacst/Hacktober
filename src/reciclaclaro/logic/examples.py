"""Ejecutar muestras sinteticas y exportar respuestas para A y C, sin API."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from reciclaclaro.contracts import (
    AcceptanceStatus, AppError, AttributeName, ConfirmedItem, PreparationStatus, ReciclaClaroError,
)
from .catalog import DEFAULT_CATALOG, _unique_keys, load_centers, text_sha256
from .comparator import compare_item

CASES_PATH = DEFAULT_CATALOG.parent / "examples" / "comparison_cases.json"


class _Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")
    acceptance: AcceptanceStatus
    preparation_status: PreparationStatus


class _Case(BaseModel):
    """Validacion de corpus local; no modifica contratos entre capas."""

    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=1)
    is_mock: Literal[True]
    center_id: str
    item: ConfirmedItem
    expected: _Expected
    expected_missing_attributes: list[AttributeName] | None = None
    expected_rule_ids: list[str] | None = None


def run_examples(cases_path: str | Path | None = None) -> list[dict]:
    centers = {center.center_id: center for center in load_centers()}
    try:
        path = CASES_PATH if cases_path is None else Path(cases_path)
        payload = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_unique_keys)
        cases = TypeAdapter(list[_Case]).validate_python(payload)
        if not cases or len({case.case_id for case in cases}) != len(cases):
            raise ValueError("El corpus debe tener casos unicos y no estar vacio")
        if any(case.center_id not in centers for case in cases):
            raise ValueError("Centro de ejemplo desconocido")
    except (OSError, ValueError) as exc:
        raise ReciclaClaroError(AppError(
            category="formato_invalido", message="Los casos sinteticos necesitan entradas y expectativas completas.",
            retryable=False,
        )) from exc
    outputs = []
    for case in cases:
        result = compare_item(case.item, centers[case.center_id])
        expected = case.expected.model_dump()
        checks = {name: getattr(result, name) == value for name, value in expected.items()}
        if case.expected_missing_attributes is not None:
            checks["missing_attributes"] = (
                sorted(q.attribute for q in result.missing_data) == sorted(case.expected_missing_attributes)
            )
        if case.expected_rule_ids is not None:
            checks["rule_ids"] = (
                sorted(ref.rule_id for ref in result.rule_references) == sorted(case.expected_rule_ids)
            )
        outputs.append({
            "case_id": case.case_id, "is_mock": True,
            "expected": expected, "result": result.model_dump(mode="json"),
            "checks": checks, "matches_expected": all(checks.values()),
        })
    return outputs


def evaluation_report(outputs: list[dict], cases_path: str | Path | None = None) -> dict:
    """Conteos reproducibles; no representan precision visual ni un benchmark."""
    path = CASES_PATH if cases_path is None else Path(cases_path)
    implementation = hashlib.sha256()
    for source in sorted([Path(__file__), Path(__file__).with_name("comparator.py"),
                          Path(__file__).with_name("catalog.py"), Path(__file__).parents[1] / "contracts.py"]):
        implementation.update(source.name.encode())
        implementation.update(source.read_text(encoding="utf-8-sig").encode("utf-8"))
    return {
        "scope": "comparador deterministico; entradas sinteticas etiquetadas manualmente",
        "is_mock": True, "live_api_tested": False, "is_benchmark": False,
        "hash_normalization": "UTF-8 sin BOM; saltos de linea LF",
        "catalog_sha256": text_sha256(DEFAULT_CATALOG),
        "cases_sha256": text_sha256(path),
        "implementation_sha256": implementation.hexdigest(),
        "total": len(outputs), "matched": sum(row["matches_expected"] for row in outputs),
        "mismatched_case_ids": [row["case_id"] for row in outputs if not row["matches_expected"]],
        "expected_acceptance_counts": dict(sorted(Counter(row["expected"]["acceptance"] for row in outputs).items())),
        "observed_acceptance_counts": dict(sorted(Counter(row["result"]["acceptance"] for row in outputs).items())),
        "checks_passed": {
            name: sum(row["checks"].get(name) is True for row in outputs)
            for name in sorted({key for row in outputs for key in row["checks"]})
        },
        "checks_total": {
            name: sum(name in row["checks"] for row in outputs)
            for name in sorted({key for row in outputs for key in row["checks"]})
        },
        "limitations": ["Muestra sintetica pequena; no mide Gemma ni impacto real.",
                        "Las fuentes publicadas no garantizan operacion actual del centro."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Guardar resultados JSON de ejemplo")
    parser.add_argument("--report", type=Path, help="Guardar conteos y huellas de la evaluacion")
    parser.add_argument("--cases", type=Path, help="Corpus sintetico alternativo")
    args = parser.parse_args()
    outputs = run_examples(args.cases)
    if args.output:
        args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report:
        args.report.write_text(json.dumps(evaluation_report(outputs, args.cases), ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    for output in outputs:
        result = output["result"]
        print(f"{output['case_id']}: {result['acceptance']} / {result['preparation_status']}")
    passed = sum(output["matches_expected"] for output in outputs)
    print(f"Ejemplos sinteticos coincidentes: {passed}/{len(outputs)}. Sin llamadas a IA.")
    return 0 if passed == len(outputs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
