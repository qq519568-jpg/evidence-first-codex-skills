#!/usr/bin/env python3
"""Validation shared by the analysis checker and HTML generator.

The validator proves that cited chart facts exist and that every narrative row
declares which maintained rule IDs it used.  It cannot prove that a traditional
rule is scientifically valid or that prose follows from a rule without human
review; callers must preserve that boundary in their reports.
"""

import json
from pathlib import Path

DIMENSIONS = [
    "立身之本", "离乡/守乡", "性格", "求财方式",
    "婚姻", "中年节奏", "健康短板", "贵人运",
]
STATUSES = {"✅叙述一致", "⚠️部分一致", "❌叙述冲突"}
VERIFICATIONS = {"未验证", "命中", "部分命中", "未命中", "未知"}
UNCERTAINTIES = {"高", "中", "低"}

RULE_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "references" / "rule-registry.json"


def _load_rule_registry():
    try:
        payload = json.loads(RULE_REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, f"规则注册表无法读取：{exc}"
    rules = payload.get("rules")
    if not isinstance(rules, list):
        return {}, "规则注册表 rules 必须是数组"
    registry = {}
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            return {}, f"规则注册表 rules[{index}] 缺少 id"
        rule_id = rule["id"]
        if rule_id in registry:
            return {}, f"规则注册表存在重复 id：{rule_id}"
        registry[rule_id] = rule
    return registry, None


def _plain(errors, path, value, allow_empty=False):
    if not isinstance(value, str):
        errors.append(f"{path} 必须是字符串")
        return
    if not allow_empty and not value.strip():
        errors.append(f"{path} 不得为空")
    if "<" in value or ">" in value:
        errors.append(f"{path} 必须是纯文本，不得包含 HTML 标签")


def _validate_bazi_basis(chart, basis, path, errors):
    if not isinstance(basis, list) or not basis:
        errors.append(f"{path} 必须是非空数组")
        return
    bz = chart.get("八字", {})
    for index, ref in enumerate(basis):
        ref_path = f"{path}[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{ref_path} 必须是对象")
            continue
        if ref.get("status") == "NOT_COMPUTED":
            if not isinstance(ref.get("reason"), str) or not ref["reason"].strip():
                errors.append(f"{ref_path}.reason 必须说明未计算原因")
            continue
        field = ref.get("field")
        if not isinstance(field, str) or not field:
            errors.append(f"{ref_path}.field 缺失")
            continue
        pillar = ref.get("pillar")
        if pillar is not None:
            target = next((p for p in bz.get("四柱", []) if p.get("柱") == pillar), None)
            if target is None:
                errors.append(f"{ref_path} 引用了不存在的四柱：{pillar}")
                continue
        else:
            target = bz
        if field not in target:
            errors.append(f"{ref_path} 引用了不存在的字段：{field}")
            continue
        actual = target[field]
        if "key" in ref:
            key = ref["key"]
            if not isinstance(actual, dict) or key not in actual:
                errors.append(f"{ref_path} 引用了不存在的子键：{key}")
                continue
            actual = actual[key]
        if "value" in ref:
            expected = ref["value"]
            if actual != expected:
                errors.append(f"{ref_path} 值不匹配：JSON={actual!r}，analysis={expected!r}")
        elif "contains" in ref:
            expected = ref["contains"]
            if not isinstance(actual, (str, list)) or expected not in actual:
                errors.append(f"{ref_path} 未包含：{expected!r}")
        else:
            errors.append(f"{ref_path} 必须提供 value 或 contains")


def _validate_ziwei_basis(chart, basis, path, errors):
    if not isinstance(basis, list) or not basis:
        errors.append(f"{path} 必须是非空数组")
        return
    zw = chart.get("紫微", {})
    if "错误" in zw:
        errors.append(f"{path} 无法验证：紫微排盘失败：{zw['错误']}")
        return
    palaces = {p.get("宫"): p for p in zw.get("十二宫", [])}
    for index, ref in enumerate(basis):
        ref_path = f"{path}[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{ref_path} 必须是对象")
            continue
        palace_name = ref.get("palace")
        if palace_name not in palaces:
            errors.append(f"{ref_path} 引用了不存在的宫位：{palace_name}")
            continue
        stars = ref.get("stars")
        if not isinstance(stars, list) or any(not isinstance(s, str) for s in stars):
            errors.append(f"{ref_path}.stars 必须是字符串数组；空宫可用空数组")
            continue
        palace = palaces[palace_name]
        available = {s.get("星") for s in palace.get("主星", [])}
        available.update(palace.get("辅星", []))
        available.update(palace.get("杂曜", []))
        missing = [s for s in stars if s not in available]
        if missing:
            errors.append(f"{ref_path} 星曜不在{palace_name}：{missing}")


def _validate_rule_ids(rule_ids, expected_domain, path, registry, errors):
    if not isinstance(rule_ids, list) or not rule_ids:
        errors.append(f"{path} 必须是非空规则 ID 数组")
        return
    if len(rule_ids) != len(set(rule_ids)):
        errors.append(f"{path} 不得包含重复规则 ID")
    for index, rule_id in enumerate(rule_ids):
        ref_path = f"{path}[{index}]"
        if not isinstance(rule_id, str) or not rule_id.strip():
            errors.append(f"{ref_path} 必须是非空字符串")
            continue
        rule = registry.get(rule_id)
        if rule is None:
            errors.append(f"{ref_path} 引用了未登记规则：{rule_id}")
            continue
        actual_domain = rule.get("domain")
        domain_matches = (actual_domain == expected_domain or
                          (expected_domain == "bazi" and isinstance(actual_domain, str)
                           and actual_domain.startswith("bazi_")))
        if not domain_matches:
            errors.append(
                f"{ref_path} 规则域不匹配：期望 {expected_domain}，实际 {actual_domain!r}"
            )


def _validate_inference(row, path, registry, errors):
    inference = row.get("inference")
    inference_path = f"{path}.inference"
    if not isinstance(inference, dict):
        errors.append(f"{inference_path} 必须是对象")
        return
    _validate_rule_ids(
        inference.get("bazi_rule_ids"), "bazi",
        f"{inference_path}.bazi_rule_ids", registry, errors,
    )
    _validate_rule_ids(
        inference.get("ziwei_rule_ids"), "ziwei",
        f"{inference_path}.ziwei_rule_ids", registry, errors,
    )
    _validate_rule_ids(
        inference.get("cross_rule_ids"), "cross",
        f"{inference_path}.cross_rule_ids", registry, errors,
    )
    if inference.get("uncertainty") not in UNCERTAINTIES:
        errors.append(
            f"{inference_path}.uncertainty 必须是高/中/低：{inference.get('uncertainty')!r}"
        )
    _plain(errors, f"{inference_path}.limitation", inference.get("limitation"))


def validate_analysis(chart, analysis):
    errors = []
    if not isinstance(chart, dict):
        return ["chart 根节点必须是对象"]
    if not isinstance(analysis, dict):
        return ["analysis 根节点必须是对象"]

    registry, registry_error = _load_rule_registry()
    if registry_error:
        errors.append(registry_error)

    if analysis.get("schema_version") != "2.1":
        errors.append("schema_version 必须是 2.1")
    for field in ("birth_info", "hexin", "footer"):
        _plain(errors, field, analysis.get(field))

    cross = analysis.get("cross")
    if not isinstance(cross, list):
        errors.append("cross 必须是数组")
    else:
        dimensions = [row.get("dimension") for row in cross if isinstance(row, dict)]
        if dimensions != DIMENSIONS:
            errors.append(f"cross 必须按固定八维度排序：{DIMENSIONS}")
        for index, row in enumerate(cross):
            path = f"cross[{index}]"
            if not isinstance(row, dict):
                errors.append(f"{path} 必须是对象")
                continue
            for field in ("dimension", "bazi", "ziwei", "status"):
                _plain(errors, f"{path}.{field}", row.get(field))
            if row.get("status") not in STATUSES:
                errors.append(f"{path}.status 非法：{row.get('status')!r}")
            _validate_bazi_basis(chart, row.get("bazi_basis"), f"{path}.bazi_basis", errors)
            _validate_ziwei_basis(chart, row.get("ziwei_basis"), f"{path}.ziwei_basis", errors)
            _validate_inference(row, path, registry, errors)

    prereg = analysis.get("prereg", [])
    if not isinstance(prereg, list):
        errors.append("prereg 必须是数组")
    else:
        for index, row in enumerate(prereg):
            path = f"prereg[{index}]"
            if not isinstance(row, dict):
                errors.append(f"{path} 必须是对象")
                continue
            for field in ("id", "prediction", "decision_window", "reasoning_level", "verification"):
                _plain(errors, f"{path}.{field}", row.get(field))
            if row.get("verification") not in VERIFICATIONS:
                errors.append(f"{path}.verification 非法：{row.get('verification')!r}")

    return errors
