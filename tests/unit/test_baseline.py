"""Unit tests for baseline diffing."""

from __future__ import annotations

from adversarial_debate.baseline import compute_fingerprint, diff_bundles


def test_fingerprint_ignores_llm_supplied_id() -> None:
    """Fingerprints must derive from stable content, not the volatile LLM `id`,
    so unchanged findings don't churn as both fixed and new across runs."""
    base = {
        "finding_type": "exploit",
        "file_path": "app.py",
        "cwe": 89,
        "code_snippet": 'query = f"... {user_id}"',
    }
    fp1 = compute_fingerprint({**base, "id": "EXPLOIT-001", "title": "run A title"})
    fp2 = compute_fingerprint({**base, "id": "EXPLOIT-999", "title": "run B title"})
    assert fp1 == fp2  # different id/title, same content => same fingerprint
    assert fp1.startswith("fp-")


def test_fingerprint_distinguishes_different_content() -> None:
    a = compute_fingerprint({"finding_type": "exploit", "file_path": "a.py", "cwe": 89})
    b = compute_fingerprint({"finding_type": "exploit", "file_path": "b.py", "cwe": 89})
    assert a != b


def test_fingerprint_honours_precomputed_value() -> None:
    assert compute_fingerprint({"fingerprint": "fp-explicit", "id": "X"}) == "fp-explicit"


def test_diff_bundles_new_and_fixed() -> None:
    baseline = {
        "findings": [
            {"fingerprint": "fp-a", "severity": "HIGH", "title": "A"},
            {"fingerprint": "fp-b", "severity": "LOW", "title": "B"},
        ]
    }
    current = {
        "findings": [
            {"fingerprint": "fp-b", "severity": "LOW", "title": "B"},
            {"fingerprint": "fp-c", "severity": "CRITICAL", "title": "C"},
        ]
    }

    diff = diff_bundles(current, baseline)
    assert [f["fingerprint"] for f in diff.new] == ["fp-c"]
    assert [f["fingerprint"] for f in diff.fixed] == ["fp-a"]
    assert [f["fingerprint"] for f in diff.existing] == ["fp-b"]
