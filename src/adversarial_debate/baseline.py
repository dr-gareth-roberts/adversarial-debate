"""Baseline/regression utilities.

Baseline workflow:
  - Save a canonical results bundle from a known-good branch as the baseline.
  - On PRs, compare the current bundle against the baseline and treat only NEW
    findings as regressions.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

SEVERITY_ORDER: dict[str, int] = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "INFO": 0,
    "UNKNOWN": -1,
}


def severity_gte(severity: str, threshold: str) -> bool:
    return SEVERITY_ORDER.get(severity.upper(), -1) >= SEVERITY_ORDER.get(threshold.upper(), 0)


def compute_fingerprint(finding: dict[str, Any]) -> str:
    """Compute a stable fingerprint for a finding."""
    explicit = finding.get("fingerprint") or finding.get("id")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()

    parts = [
        str(finding.get("finding_type", "")).strip(),
        str(finding.get("agent", "")).strip(),
        str(finding.get("file_path", "")).strip(),
        str(finding.get("line", "")).strip(),
        str(finding.get("title", "")).strip(),
    ]
    raw = "\n".join(parts).encode("utf-8", errors="replace")
    return "fp-" + hashlib.sha256(raw).hexdigest()[:16]


def index_by_fingerprint(findings: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for f in findings:
        fp = compute_fingerprint(f)
        if fp and fp not in indexed:
            indexed[fp] = f
    return indexed


@dataclass(frozen=True)
class BaselineDiff:
    new: list[dict[str, Any]]
    fixed: list[dict[str, Any]]
    existing: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "new_count": len(self.new),
            "fixed_count": len(self.fixed),
            "existing_count": len(self.existing),
            "new": self.new,
            "fixed": self.fixed,
        }


def diff_bundles(current: dict[str, Any], baseline: dict[str, Any]) -> BaselineDiff:
    current_findings = current.get("findings", []) or []
    baseline_findings = baseline.get("findings", []) or []

    cur = index_by_fingerprint(current_findings)
    base = index_by_fingerprint(baseline_findings)

    new = [cur[fp] for fp in sorted(set(cur) - set(base))]
    fixed = [base[fp] for fp in sorted(set(base) - set(cur))]
    existing = [cur[fp] for fp in sorted(set(cur) & set(base))]
    return BaselineDiff(new=new, fixed=fixed, existing=existing)
