#!/usr/bin/env python3
"""Block Blender execution unless every scene Asset_ID is APPROVED."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from validate_asset_manifest import validate_row


ASSET_ID = re.compile(r"^\s*Asset_ID:\s*[\"']?([^\s#\"']+)", re.MULTILINE)


def scalar(text: str, key: str) -> str | None:
    pattern = re.compile(rf"^\s*{re.escape(key)}:\s*[\"']?([^\s#\"']+)", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scene", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    scene = args.scene.resolve()
    manifest = args.manifest.resolve()
    text = scene.read_text(encoding="utf-8-sig")
    errors: list[str] = []

    expected = {
        "Local_Library_Searched": "true",
        "Copyright_Gate_Passed": "true",
        "Manifest_Validation": "PASS",
        "Reject_Non_Approved_Assets": "true",
    }
    for key, wanted in expected.items():
        actual = scalar(text, key)
        if actual is None or actual.lower() != wanted.lower():
            errors.append(f"scene preflight requires {key}: {wanted} (found {actual!r})")

    ids = ASSET_ID.findall(text)
    if not ids:
        errors.append("scene contains no Asset_ID entries")
    if any("<" in item or ">" in item for item in ids):
        errors.append("scene contains unresolved Asset_ID placeholders")

    rows: dict[str, dict[str, str]] = {}
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            asset_id = row.get("asset_id", "").strip()
            if asset_id:
                rows[asset_id] = row
            errors.extend(validate_row(row, line, manifest))

    for asset_id in ids:
        row = rows.get(asset_id)
        if row is None:
            errors.append(f"Asset_ID not found in manifest: {asset_id}")
        elif row.get("status", "").strip() != "APPROVED":
            errors.append(f"Asset_ID {asset_id} is {row.get('status')!r}, not APPROVED")

    if errors:
        print(f"BLOCKED: {len(errors)} scene asset gate issue(s)")
        for error in errors:
            print("- " + error)
        return 1
    print(f"PASS: scene may enter Blender; {len(ids)} APPROVED asset reference(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
