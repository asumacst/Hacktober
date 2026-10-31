"""La evaluacion exige expectativas completas y datos declarados sinteticos."""

import json

import pytest

from reciclaclaro.contracts import ReciclaClaroError
from reciclaclaro.logic.examples import CASES_PATH, evaluation_report, run_examples
from reciclaclaro.logic.audit import profile_catalog
from reciclaclaro.logic.catalog import text_sha256


@pytest.mark.parametrize("problem", [
    "empty", "no_expected", "no_preparation", "extra_expected", "wrong_status",
    "duplicate_case", "unknown_center", "not_mock", "unexpected_field",
])
def test_incomplete_evaluation_is_not_reported_as_success(problem, tmp_path):
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if problem == "empty":
        cases = []
    elif problem == "no_expected":
        cases[0]["expected"] = {}
    elif problem == "no_preparation":
        del cases[0]["expected"]["preparation_status"]
    elif problem == "extra_expected":
        cases[0]["expected"]["invented"] = True
    elif problem == "wrong_status":
        cases[0]["expected"]["acceptance"] = "invented"
    elif problem == "duplicate_case":
        cases.append(cases[0])
    elif problem == "unknown_center":
        cases[0]["center_id"] = "no-existe"
    elif problem == "not_mock":
        cases[0]["is_mock"] = False
    elif problem == "unexpected_field":
        cases[0]["expected_resut"] = "typo"
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    with pytest.raises(ReciclaClaroError):
        run_examples(cases_path=path)


def test_wrong_expected_result_is_reported_as_failure(tmp_path):
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))[:1]
    cases[0]["expected"]["acceptance"] = "rejected"
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    result = run_examples(cases_path=path)
    assert result[0]["matches_expected"] is False
    report = evaluation_report(result, path)
    assert report["matched"] == 0
    assert report["mismatched_case_ids"] == [cases[0]["case_id"]]


@pytest.mark.parametrize("field,value", [
    ("expected_missing_attributes", ["material"]), ("expected_rule_ids", ["nonexistent-rule"]),
])
def test_correct_status_cannot_hide_wrong_questions_or_sources(field, value, tmp_path):
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))[:1]
    cases[0][field] = value
    path = tmp_path / "cases.json"
    path.write_text(json.dumps(cases), encoding="utf-8")
    assert run_examples(path)[0]["matches_expected"] is False


def test_evaluation_counts_are_reproducible_and_not_ai_accuracy():
    outputs = run_examples()
    report = evaluation_report(outputs)
    assert report == evaluation_report(run_examples())
    assert report["matched"] == report["total"] == len(outputs)
    assert report["live_api_tested"] is False
    assert report["is_benchmark"] is False
    assert len(report["implementation_sha256"]) == 64
    assert sum(report["expected_acceptance_counts"].values()) == len(outputs)


def test_quality_profile_preserves_missing_dates_and_pending_rule():
    report = profile_catalog()
    assert report["rules_with_evidence"] == report["rules"]
    assert report["sources_without_publication_date"] == report["unique_source_records"]
    assert report["unresolved_rule_ids"] == ["fas-car-pp-envase-por-confirmar"]
    glass = next(row for row in report["required_confirmations"] if row["rule_id"] == "fas-car-vidrio-envase")
    assert "presentation" in glass["acceptance_attributes"]
    assert "boxed" in glass["preparation_attributes"]


def test_saved_example_responses_match_current_code_and_inputs():
    saved = json.loads((CASES_PATH.parent / "comparison_results.json").read_text(encoding="utf-8"))
    assert saved == run_examples()


def test_saved_evaluation_report_has_current_input_and_implementation_hashes():
    saved = json.loads((CASES_PATH.parent / "evaluation_report.json").read_text(encoding="utf-8"))
    assert saved == evaluation_report(run_examples())


def test_saved_quality_report_matches_current_catalog():
    saved = json.loads((CASES_PATH.parents[1] / "quality_report.json").read_text(encoding="utf-8"))
    assert saved == profile_catalog()


def test_text_hash_is_stable_across_windows_and_unix_line_endings(tmp_path):
    windows = tmp_path / "windows.txt"
    unix = tmp_path / "unix.txt"
    windows.write_bytes(b"\xef\xbb\xbfa\r\nb\r\n")
    unix.write_bytes(b"a\nb\n")
    assert text_sha256(windows) == text_sha256(unix)
