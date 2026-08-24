#!/usr/bin/env python3
"""Public smoke test using synthetic input only."""

import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from redact_chart import redact_chart  # noqa: E402


def run(command):
    result = subprocess.run(
        command,
        cwd=SCRIPTS,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr[:1000])
    return result.stdout


chart_text = run(
    [
        sys.executable,
        "-X",
        "utf8",
        str(SCRIPTS / "calc_chart.py"),
        "--date",
        "2000-01-01",
        "--time",
        "12:30",
        "--sex",
        "男",
        "--place",
        "虚构示例地",
        "--timezone",
        "Asia/Shanghai",
    ]
)
chart = json.loads(chart_text)
assert "输入" in chart and "八字" in chart and "紫微" in chart

shared = redact_chart(chart)
serialized = json.dumps(shared, ensure_ascii=False)
assert "2000-01-01" not in serialized
assert "虚构示例地" not in serialized
assert shared["_share_meta"]["redaction_level"] == "direct_identifiers_only"

node = shutil.which("node")
if node:
    ziwei_text = run([node, str(SCRIPTS / "calc_ziwei.js"), "2000-01-01", "6", "男"])
    ziwei = json.loads(ziwei_text)
    assert ziwei["_meta"]["引擎"] == "iztro"
    assert len(ziwei["十二宫"]) == 12

print("PASS: synthetic Bazi calculation, redaction, and available Ziwei runtime")
