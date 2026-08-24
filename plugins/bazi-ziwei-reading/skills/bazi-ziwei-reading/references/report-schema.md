# 海报分析数据 schema v2.1

海报数据由两部分组成：`chart.json` 是排盘事实；`analysis.json` 是传统解释。解释必须携带可机器核对的依据引用。

## analysis.json

```json
{
  "schema_version": "2.1",
  "birth_info": "公历 2000-01-01 12:30，男，虚构示例地，Asia/Shanghai",
  "hexin": "核心总评纯文本；不要写 HTML。",
  "cross": [
    {
      "dimension": "立身之本",
      "bazi": "八字结论",
      "bazi_basis": [
        {"pillar": "月", "field": "干支", "value": "戊辰"},
        {"field": "日主", "value": "丁"}
      ],
      "ziwei": "紫微结论",
      "ziwei_basis": [
        {"palace": "命宫", "stars": ["紫微", "破军"]}
      ],
      "inference": {
        "bazi_rule_ids": ["BZ-OBS-001"],
        "ziwei_rule_ids": ["ZW-PALACE-001"],
        "cross_rule_ids": ["CROSS-NARRATIVE-001"],
        "uncertainty": "高",
        "limitation": "传统象征叙述，不是对真人的事实判断。"
      },
      "status": "⚠️部分一致"
    }
  ],
  "prereg": [
    {
      "id": "1",
      "prediction": "按传统规则锁定的可判别文本",
      "decision_window": "2031-2040",
      "reasoning_level": "B",
      "verification": "未验证"
    }
  ],
  "footer": "命理为传统解释系统，供参照，非定数。"
}
```

## 约束

- `cross` 在双盘海报中必须包含八个固定维度：立身之本、离乡/守乡、性格、求财方式、婚姻、中年节奏、健康短板、贵人运。
- `ziwei_basis[].palace` 必须存在于 `chart.json` 的十二宫；`stars` 必须真实存在于该宫的主星、辅星或杂曜中。
- `bazi_basis` 带 `pillar` 时按四柱中的柱名与字段核对；不带 `pillar` 时按八字顶层字段核对。
- 普通字段用 `value` 做精确匹配；数组或文本可用 `contains`；字典子项可增加 `key` 后再用 `value` 匹配。
- 明确未计算的依据使用 `{"status":"NOT_COMPUTED","reason":"..."}`，不得用无关字段充当依据。
- `status` 只能是 `✅叙述一致`、`⚠️部分一致`、`❌叙述冲突`。
- 每个 `cross[]` 都必须提供 `inference`。其中三组规则 ID 必须存在于 [rule-registry.json](rule-registry.json)，并分别属于 `bazi`、`ziwei`、`cross` 域。
- `uncertainty` 只能是高/中/低；`limitation` 必须具体说明本行不能推出什么。规则 ID 只保证推演路径可追踪，不证明结论正确，仍需人工复核“前提是否足以推出结论”。
- 所有文本字段都是纯文本。生成器负责 HTML 转义，禁止传入标签或脚本。
- `verification` 只能是 `未验证`、`命中`、`部分命中`、`未命中`、`未知`。

运行 `scripts/validate_analysis.py` 验证。验证失败时不得生成海报。
