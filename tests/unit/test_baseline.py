"""Unit tests for baseline diffing."""

from __future__ import annotations

from adversarial_debate.baseline import diff_bundles


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
