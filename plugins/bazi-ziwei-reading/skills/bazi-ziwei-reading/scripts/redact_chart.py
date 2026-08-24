#!/usr/bin/env python3
"""Remove direct birth identifiers from a chart before voluntary sharing."""

import argparse
from copy import deepcopy
import json
import sys


def redact_chart(chart):
    output = deepcopy(chart)
    output["输入"] = {
        "redaction_status": "DIRECT_IDENTIFIERS_REMOVED",
        "warning": "命盘结构本身仍可能具有可识别性；仅在必要范围内分享。",
    }
    ziwei = output.get("紫微")
    if isinstance(ziwei, dict):
        for field in ("农历", "生肖", "星座"):
            ziwei.pop(field, None)
    output["_share_meta"] = {
        "redaction_level": "direct_identifiers_only",
        "removed": [
            "公历日期", "当地民用时间", "当地民用小时", "当地民用分钟", "时辰序号", "性别参数",
            "出生地", "时区", "紫微农历", "生肖", "星座",
        ],
        "residual_risk": "四柱、星曜和大运等结构仍可能缩小出生时间范围，不属于匿名化保证。",
    }
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart", required=True)
    parser.add_argument("--output", help="省略时输出到 stdout")
    args = parser.parse_args()
    with open(args.chart, encoding="utf-8-sig") as handle:
        chart = json.load(handle)
    payload = json.dumps(redact_chart(chart), ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        print(f"PASS direct identifiers removed -> {args.output}")
    else:
        sys.stdout.write(payload + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
