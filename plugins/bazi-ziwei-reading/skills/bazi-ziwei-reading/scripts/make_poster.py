#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render validated chart facts and plain-text analysis into a single HTML file."""

import argparse
import html
import json
import os
import re
import sys

from analysis_schema import validate_analysis

TPL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "report-poster.html")
WX_CLASS = {"木": "wx-木", "火": "wx-火", "土": "wx-土", "金": "wx-金", "水": "wx-水"}
SIHUA_COLOR = {"禄": "si-lord", "权": "si-lord", "科": "si-lord", "忌": "ji"}


def esc(value):
    return html.escape(str(value), quote=True)


def paragraphs(value):
    parts = [part.strip() for part in str(value).split("\n\n") if part.strip()]
    return "".join(f"<p>{esc(part)}</p>" for part in parts)


def pillars_html(bz):
    ganzhi_row = "<tr><th>干支</th>"
    shishen_row = "<tr><th>十神</th>"
    cang_row = "<tr><th>藏干</th>"
    for pillar in bz["四柱"]:
        ganzhi_row += f"<td class='pillar-ganzhi'>{esc(pillar['干支'])}</td>"
        shishen_row += f"<td>{esc(pillar['天干十神'])}</td>"
        cang = " ".join(f"{item['干']}({item['十神']})" for item in pillar["地支藏干"])
        cang_row += f"<td><div class='canggan'>{esc(cang)}</div></td>"
    return "\n    ".join((ganzhi_row + "</tr>", shishen_row + "</tr>", cang_row + "</tr>"))


def wuxing_html(bz):
    total = sum(bz["五行统计"].values())
    bars, notes = [], []
    for element, count in bz["五行统计"].items():
        percent = count * 100 // total if total else 0
        bars.append(f'<div class="{WX_CLASS[element]}" style="width:{percent}%;">{esc(element)}{count}</div>')
        notes.append(f"{element}{count}")
    note = (
        f"未加权计数（天干+地支本气）：{' / '.join(notes)}；"
        f"空亡：{bz['空亡']}；大运{bz['大运方向']}，起运{bz['起运虚岁']}岁。"
    )
    return "".join(bars), esc(note)


def ziwei_html(zw):
    cells = []
    for palace in zw["十二宫"]:
        star_html = ""
        for star in palace["主星"] or []:
            mutagen = star["四化"]
            css_class = SIHUA_COLOR.get(mutagen, "")
            star_html += f'<span class="{css_class}">{esc(star["星"])}</span>'
            if mutagen:
                star_html += f'<span class="{css_class}">{esc(mutagen)}</span>'
            if star["亮度"]:
                star_html += f'<sup>{esc(star["亮度"])}</sup>'
            star_html += " "
        minor = " ".join((palace["辅星"] or [])[:6]) + " " + " ".join((palace["杂曜"] or [])[:4])
        cells.append(
            f'<div class="palace"><div class="p-name">{esc(palace["宫"])}</div>'
            f'<div class="p-gz">{esc(palace["宫干支"])}</div>'
            f'<div class="p-star">{star_html or "—"}</div>'
            f'<div class="p-minor">{esc(minor.strip())}</div>'
            f'<div class="p-decadal">{esc(palace["大限"])}</div></div>'
        )
    return "\n    ".join(cells)


def bazi_basis_text(refs):
    parts = []
    for ref in refs:
        if ref.get("status") == "NOT_COMPUTED":
            parts.append(f"NOT_COMPUTED：{ref.get('reason', '')}")
            continue
        prefix = ref.get("pillar", "")
        key = f".{ref['key']}" if "key" in ref else ""
        operator = "包含" if "contains" in ref else "="
        value = ref.get("contains", ref.get("value"))
        parts.append(f"{prefix}{ref['field']}{key}{operator}{value}")
    return "；".join(parts)


def ziwei_basis_text(refs):
    parts = []
    for ref in refs:
        stars = "、".join(ref["stars"]) if ref["stars"] else "空宫"
        parts.append(f"{ref['palace']}：{stars}")
    return "；".join(parts)


def inference_text(inference, side):
    rule_ids = inference[f"{side}_rule_ids"]
    return (
        f"规则：{'、'.join(rule_ids)}；不确定性：{inference['uncertainty']}；"
        f"边界：{inference['limitation']}"
    )


def cross_html(rows):
    rendered = []
    for row in rows:
        inference = row["inference"]
        bazi = (
            f"{esc(row['bazi'])}<small>依据：{esc(bazi_basis_text(row['bazi_basis']))}</small>"
            f"<small>{esc(inference_text(inference, 'bazi'))}</small>"
        )
        ziwei = (
            f"{esc(row['ziwei'])}<small>依据：{esc(ziwei_basis_text(row['ziwei_basis']))}</small>"
            f"<small>{esc(inference_text(inference, 'ziwei'))}</small>"
        )
        status = (
            f"{esc(row['status'])}<small>对照规则："
            f"{esc('、'.join(inference['cross_rule_ids']))}</small>"
        )
        rendered.append(
            f"<tr><td>{esc(row['dimension'])}</td><td>{bazi}</td><td>{ziwei}</td><td>{status}</td></tr>"
        )
    return "\n    ".join(rendered)


def prereg_html(rows):
    if not rows:
        return '<tr><td colspan="4">未启用预注册；未读取或回填用户经历。</td></tr>'
    return "\n    ".join(
        f"<tr><td>{esc(row['id'])}</td><td>{esc(row['prediction'])}</td>"
        f"<td>{esc(row['decision_window'])}</td><td>{esc(row['reasoning_level'])} / {esc(row['verification'])}</td></tr>"
        for row in rows
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chart", required=True)
    parser.add_argument("--analysis", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    with open(args.chart, encoding="utf-8-sig") as handle:
        chart = json.load(handle)
    with open(args.analysis, encoding="utf-8-sig") as handle:
        analysis = json.load(handle)
    errors = validate_analysis(chart, analysis)
    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    bz, zw = chart["八字"], chart["紫微"]
    if "错误" in zw:
        print(f"FAIL 紫微排盘错误：{zw['错误']}", file=sys.stderr)
        return 1
    if len(zw.get("十二宫", [])) != 12:
        print(f"FAIL 紫微宫位数量应为12，实际为{len(zw.get('十二宫', []))}", file=sys.stderr)
        return 1

    with open(TPL, encoding="utf-8") as handle:
        output = handle.read()
    bars, note = wuxing_html(bz)
    output = (
        output.replace("{{TITLE}}", "命盘叙述一致性比较")
        .replace("{{BIRTH_INFO}}", esc(analysis["birth_info"]))
        .replace("{{BAZI_PILLARS_HTML}}", pillars_html(bz))
        .replace("{{WUXING_BAR_HTML}}", bars)
        .replace("{{WUXING_NOTE}}", note)
        .replace("{{ZIWEI_GRID_HTML}}", ziwei_html(zw))
        .replace("{{HEXIN_HTML}}", paragraphs(analysis["hexin"]))
        .replace("{{CROSS_HTML}}", cross_html(analysis["cross"]))
        .replace("{{PREREG_HTML}}", prereg_html(analysis.get("prereg", [])))
        .replace("{{FOOTER_NOTE}}", esc(analysis["footer"]))
    )
    placeholders = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", output)))
    if placeholders:
        print(f"FAIL 残留占位符：{placeholders}", file=sys.stderr)
        return 1

    with open(args.output, "w", encoding="utf-8") as handle:
        handle.write(output)
    print(f"PASS -> {args.output} ({len(output.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
