"""Ejecutar muestras sinteticas y exportar respuestas para A y C, sin API."""

import argparse
import json
from pathlib import Path

from reciclaclaro.contracts import ConfirmedItem
from .catalog import DEFAULT_CATALOG, load_centers
from .comparator import compare_item

CASES_PATH = DEFAULT_CATALOG.parent / "examples" / "comparison_cases.json"


def run_examples() -> list[dict]:
    centers = {center.center_id: center for center in load_centers()}
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    outputs = []
    for case in cases:
        item = ConfirmedItem.model_validate(case["item"])
        result = compare_item(item, centers[case["center_id"]])
        outputs.append({
            "case_id": case["case_id"], "is_mock": True,
            "expected": case["expected"], "result": result.model_dump(mode="json"),
            "matches_expected": all(getattr(result, name) == value
                                    for name, value in case["expected"].items()),
        })
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Guardar resultados JSON de ejemplo")
    args = parser.parse_args()
    outputs = run_examples()
    if args.output:
        args.output.write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for output in outputs:
        result = output["result"]
        print(f"{output['case_id']}: {result['acceptance']} / {result['preparation_status']}")
    passed = sum(output["matches_expected"] for output in outputs)
    print(f"Ejemplos sinteticos coincidentes: {passed}/{len(outputs)}. Sin llamadas a IA.")
    return 0 if passed == len(outputs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
