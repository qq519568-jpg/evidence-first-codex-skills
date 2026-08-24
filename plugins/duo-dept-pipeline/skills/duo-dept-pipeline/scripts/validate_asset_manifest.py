#!/usr/bin/env python3
"""Validate the dual-department Blender asset manifest copyright gate."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


REQUIRED = {
    "asset_id", "name_cn", "category", "status", "rights_class",
    "source_url", "source_author", "license_code", "license_url",
    "evidence_file", "evidence_date", "commercial_use",
    "derivatives_allowed", "rendered_output_allowed",
    "attribution_required", "attribution_text", "third_party_ip_clear",
    "source_hash_sha256", "source_path", "blend_file", "preview_file",
    "technical_reviewer", "visual_reviewer", "notes",
}

STATUSES = {
    "REQUESTED", "SOURCE_REVIEW", "HOLD_LICENSE", "REJECTED", "INBOX",
    "REVIEW_TECH", "REVIEW_VISUAL", "APPROVED", "QUARANTINED", "ARCHIVED",
}
RIGHTS = {
    "UNKNOWN", "GREEN_SELF", "GREEN_CC0", "GREEN_CCBY",
    "GREEN_COMMERCIAL", "HOLD_LICENSE", "REJECTED",
}
AUTO_LICENSES = {"CC0-1.0", "PUBLIC-DOMAIN", "SELF-OWNED"}
CONDITIONAL_LICENSES = {"CC-BY-4.0", "COMMERCIAL-CUSTOM"}
TRUE = {"true", "yes", "1"}
FALSE = {"false", "no", "0"}
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def truth(value: str) -> bool:
    return value.strip().lower() in TRUE


def exists(raw: str, manifest: Path) -> bool:
    value = raw.strip()
    if not value:
        return False
    path = Path(value)
    if not path.is_absolute():
        path = manifest.parent / path
    return path.exists()


def validate_row(row: dict[str, str], line: int, manifest: Path) -> list[str]:
    errors: list[str] = []
    asset = row.get("asset_id", "").strip() or f"line-{line}"
    status = row.get("status", "").strip()
    rights = row.get("rights_class", "").strip()
    license_code = row.get("license_code", "").strip().upper()

    def err(message: str) -> None:
        errors.append(f"{asset} (line {line}): {message}")

    if status not in STATUSES:
        err(f"invalid status {status!r}")
    if rights not in RIGHTS:
        err(f"invalid rights_class {rights!r}")

    if status not in {"REQUESTED", "SOURCE_REVIEW", "REJECTED"}:
        for field in ("source_url", "source_author", "license_code", "evidence_file", "evidence_date", "source_hash_sha256"):
            if not row.get(field, "").strip():
                err(f"missing {field}")

    sha = row.get("source_hash_sha256", "").strip()
    if sha and not SHA256.fullmatch(sha):
        err("source_hash_sha256 must be 64 hexadecimal characters")

    evidence = row.get("evidence_file", "")
    if evidence and not exists(evidence, manifest):
        err(f"evidence_file does not exist: {evidence}")

    if status == "APPROVED":
        if rights not in {"GREEN_SELF", "GREEN_CC0", "GREEN_CCBY", "GREEN_COMMERCIAL"}:
            err("APPROVED requires a GREEN rights_class")
        if license_code not in AUTO_LICENSES | CONDITIONAL_LICENSES:
            err(f"APPROVED license not permitted by policy: {license_code!r}")
        for field in ("commercial_use", "derivatives_allowed", "rendered_output_allowed", "third_party_ip_clear"):
            if not truth(row.get(field, "")):
                err(f"APPROVED requires {field}=true")
        if truth(row.get("attribution_required", "")) and not row.get("attribution_text", "").strip():
            err("attribution_text required when attribution_required=true")
        for field in ("blend_file", "preview_file", "technical_reviewer", "visual_reviewer"):
            if not row.get(field, "").strip():
                err(f"APPROVED requires {field}")
        for field in ("blend_file", "preview_file"):
            value = row.get(field, "")
            if value and not exists(value, manifest):
                err(f"{field} does not exist: {value}")

    if rights in {"HOLD_LICENSE", "UNKNOWN"} and status == "APPROVED":
        err("unknown or held rights cannot be APPROVED")
    if license_code.startswith("CC-BY-NC") or "-ND" in license_code:
        err(f"forbidden license for this production policy: {license_code}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = args.manifest.resolve()

    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED - fields)
        if missing:
            print("FAIL: missing columns: " + ", ".join(missing))
            return 2
        errors: list[str] = []
        count = 0
        for line, row in enumerate(reader, start=2):
            count += 1
            errors.extend(validate_row(row, line, manifest))

    if errors:
        print(f"FAIL: {len(errors)} issue(s) in {count} asset(s)")
        for item in errors:
            print("- " + item)
        return 1
    print(f"PASS: copyright and asset manifest gate passed for {count} asset(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
