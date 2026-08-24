#!/usr/bin/env python3
"""Calculate two candidate birth hours independently and emit a factual diff."""

import argparse
import json
from pathlib import Path
import subprocess
import sys

CALC = Path(__file__).resolve().parent / "calc_chart.py"


def _candidate_args(args, suffix):
    hour = getattr(args, f"hour_{suffix}")
    time_index = getattr(args, f"time_index_{suffix}")
    values = ["--date", args.date, "--sex", args.sex, "--place", args.place,
              "--timezone", args.timezone]
    if hour is not None:
        values.extend(["--hour", str(hour)])
        label = f"hour={hour}"
    else:
        values.extend(["--time-index", str(time_index)])
        label = f"time-index={time_index}"
    return values, label


def _run_chart(values):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(CALC), *values],
        capture_output=True, encoding="utf-8", timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"calc_chart.py exited {result.returncode}")
    return json.loads(result.stdout)


def _pillar_map(chart):
    return {item["柱"]: item["干支"] for item in chart["八字"]["四柱"]}


def _ziwei_summary(chart):
    ziwei = chart.get("紫微", {})
    if "错误" in ziwei:
        return {"status": "NOT_COMPUTED", "reason": ziwei["错误"]}
    palace_stars = {}
    for palace in ziwei.get("十二宫", []):
        stars = [item.get("星") for item in palace.get("主星", [])]
        stars.extend(palace.get("辅星", []))
        stars.extend(palace.get("杂曜", []))
        palace_stars[palace.get("宫")] = {
            "branch": palace.get("宫干支", "")[-1:],
            "stars": stars,
            "decadal": palace.get("大限"),
        }
    return {
        "status": "COMPUTED",
        "命宫": ziwei.get("命宫"),
        "身宫": ziwei.get("身宫"),
        "五行局": ziwei.get("五行局"),
        "palaces": palace_stars,
    }


def build_diff(first, second, first_label, second_label):
    first_pillars, second_pillars = _pillar_map(first), _pillar_map(second)
    bazi_changes = [
        {"field": f"{pillar}柱", first_label: first_pillars[pillar], second_label: second_pillars[pillar]}
        for pillar in ("年", "月", "日", "时")
        if first_pillars[pillar] != second_pillars[pillar]
    ]
    first_ziwei, second_ziwei = _ziwei_summary(first), _ziwei_summary(second)
    ziwei_changes = []
    if first_ziwei["status"] == second_ziwei["status"] == "COMPUTED":
        for field in ("命宫", "身宫", "五行局"):
            if first_ziwei[field] != second_ziwei[field]:
                ziwei_changes.append(
                    {"field": field, first_label: first_ziwei[field], second_label: second_ziwei[field]}
                )
        for palace in sorted(set(first_ziwei["palaces"]) | set(second_ziwei["palaces"])):
            if first_ziwei["palaces"].get(palace) != second_ziwei["palaces"].get(palace):
                ziwei_changes.append({
                    "field": f"十二宫.{palace}",
                    first_label: first_ziwei["palaces"].get(palace),
                    second_label: second_ziwei["palaces"].get(palace),
                })
    else:
        ziwei_changes.append({"field": "紫微计算状态", first_label: first_ziwei, second_label: second_ziwei})
    return {
        "schema_version": "1.0",
        "candidate_labels": [first_label, second_label],
        "bazi_changes": bazi_changes,
        "ziwei_changes": ziwei_changes,
        "interpretation_status": "NOT_COMPUTED",
        "warnings": [
            "本工具只比较确定性盘面差异，不根据主观吻合度认定出生时辰。",
            "日期、地点与时区按已确认的当地民用时处理；未执行真太阳时、经度或夏令时换算。",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    parser.add_argument("--sex", required=True, choices=["男", "女"])
    parser.add_argument("--place", default="未提供")
    parser.add_argument("--timezone", default="未提供")
    group_a = parser.add_mutually_exclusive_group(required=True)
    group_a.add_argument("--hour-a", type=int)
    group_a.add_argument("--time-index-a", type=int)
    group_b = parser.add_mutually_exclusive_group(required=True)
    group_b.add_argument("--hour-b", type=int)
    group_b.add_argument("--time-index-b", type=int)
    args = parser.parse_args()

    first_args, first_label = _candidate_args(args, "a")
    second_args, second_label = _candidate_args(args, "b")
    first = _run_chart(first_args)
    second = _run_chart(second_args)
    print(json.dumps(build_diff(first, second, first_label, second_label), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
