---
name: bazi-ziwei-reading
description: 按用户明确要求，用脚本排算八字四柱或紫微斗数，并以传统文化解释框架提供有依据、标注不确定性的解读；仅在用户提供或准备提供出生资料并要求八字、四柱、紫微、命盘、大运、流年、用神、格局或双盘对照时使用。不要因普通日期换算、传统文化介绍、星座讨论、性格聊天或编程问题触发。
---

# 八字与紫微排盘解读

把排盘事实、传统规则推演和现实建议严格分开。命理属于传统解释系统，不是经科学验证的预测工具；不得把内部推演标签写成科学证据或概率。

## 先选模式

只完成用户实际要求的模式，不自动扩大交付范围：

- **八字模式**：只排八字并读取 [references/bazi-method.md](references/bazi-method.md)。用户明确要求“收费级、专业详批、完整交付”时，再读取并同时执行 [references/bazi-client-voice.md](references/bazi-client-voice.md) 与 [references/bazi-professional-report.md](references/bazi-professional-report.md)：前者管客户能否先听懂，后者管专业推导能否复核。
- **紫微模式**：只排紫微并读取 [references/ziwei-method.md](references/ziwei-method.md)。用户明确要求“收费级、专业详批、完整交付”时，再读取并同时执行 [references/ziwei-client-voice.md](references/ziwei-client-voice.md) 与 [references/ziwei-professional-report.md](references/ziwei-professional-report.md)：前者管命身与阶段主线能否先听懂，后者管宫位、星曜、四化和大限能否复核。
- **双盘模式**：仅当用户明确要求双盘、互证或综合解读时，同时完成前两种模式，再读取 [references/cross-validate.md](references/cross-validate.md)。若用户要求收费级双盘，八字和紫微各自先通过本体系的客户口吻与专业交付规范，再做叙述对照；不得用一套话术覆盖两盘。
- **海报模式**：仅当用户要求 HTML、海报或分享页时，在已完成相应解读后生成；不要为海报新增断语。

若用户只说“看看八字”或“排个紫微”，不要输出另一套体系。若用户要求简批，遵守其长度；只有明确要求“详批”时才使用完整章节模板；“收费级/专业详批”须通过所选体系专业交付规范的十二项门槛。

## 收集输入

执行前读取 [references/input-contract.md](references/input-contract.md)，确认以下字段：

- 公历出生日期；当前脚本不直接接受农历。用户只提供农历时，先确认闰月并用可审计的历法工具转换，向用户展示转换结果后再排盘。
- 出生时间；八字至少精确到时辰，紫微需要时辰序号。时间未知时不得假造。
- 排盘规则所需的男/女参数。说明这是传统排盘引擎的二元计算参数，不等同于用户的性别认同。
- 出生地与时区。脚本按用户提供的当地民用时记录，不执行真太阳时、经度或夏令时换算。
- 换日口径。当前实现固定采用午夜 00:00 换日，23:00 仍按输入日期；用户要求其他流派口径时停止并说明脚本暂不支持。

时辰交界、日期转换或时区仍有歧义时，先问一个简短问题。必要时用 `scripts/compare_candidate_hours.py` 分别计算两个候选时辰并只报告盘面差异；不得混合结论，也不得根据主观吻合度宣布某个时辰已被验证。

## 排算

必须运行脚本，禁止模型手排：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_calc.ps1 -BirthDate 2000-01-01 -BirthTime 12:30 -Sex 男 -Place "虚构示例地" -Timezone "Asia/Shanghai"
```

公共仓库不提交依赖缓存。首次使用前，在用户同意联网安装依赖后运行`scripts/setup_dependencies.ps1`；它把`lunar_python` 1.4.8安装到`scripts/vendor/`并用`npm ci`安装`iztro` 2.5.8。依赖缺失时先说明并请求安装授权，不得改用模型手排。Windows 启动器会依次查找系统 Python 和 Codex 自带 Python；非 Windows 环境可按`requirements.txt`与`scripts/package-lock.json`安装后直接运行`python -X utf8 scripts/calc_chart.py ...`。

优先使用 `--time HH:MM` 保留分钟。兼容输入还有 `--hour`，以及 `--time-index`：`0早子 1丑 2寅 3卯 4辰 5巳 6午 7未 8申 9酉 10戌 11亥 12晚子`。用户明确要求具体流年时，可在 PowerShell 传入 `-FlowYear @(2026,2027)`（直接 Python 则重复 `--flow-year`）；未请求时不计算。

运行规则：

1. `--time`、`--hour` 与 `--time-index` 三选一；有分钟时禁止降级成整点。输入越界或依赖缺失时停止，不得用模型补算。
2. 先保存完整 JSON，再写分析。排盘事实只能来自该 JSON；对外分享前优先运行 `scripts/redact_chart.py` 去除直接身份字段，并说明命盘结构仍有残余识别风险。
3. “五行统计”只是天干与地支本气的未加权计数，不等于旺衰强度。
4. 八字流年只在明确传入目标年后输出干支、大运归属和机械关系；这些字段不自动构成事件预测。没有脚本生成的紫微流年四化或年度结构时，不写紫微逐年预测，标记 `NOT_COMPUTED`。
5. `起运.起运时长.年` 是从出生到起运的经过年数，不是虚岁；虚岁必须引用 `起运.起运虚岁` 或各运 `起止虚岁`。交运年份还要查看精确 `交运公历`。
6. 修改脚本后用同一 Python 运行 `tests/README.md` 列出的全部自动测试，并运行 `powershell -File scripts/validate_skill_structure.ps1`。`tests/evals/validate_suite.py` 只验证行为评测规格，不等于真实模型前向测试已执行。

## 写解读

每条内容使用三层标识：

- **排盘事实**：直接引用 JSON 字段，如四柱、星曜、四化、大运、大限。
- **传统推演**：注明依据与内部推演层级。`S0-S3/A-E` 仅表示信息来源和规则距离，不表示科学证据强度。
- **现实建议**：写成低风险、可自主选择的参考，不从命盘推出医学诊断、投资指令、法律判断或重大人生决定。

重大判断须给出依据、[references/rule-registry.json](references/rule-registry.json) 中的规则 ID、已满足条件、反证和不确定度。规则 ID 只让推演路径可追踪，不能证明结论成立；交付前仍要人工检查“这些前提是否足以推出该结论”。盘面不支持时明确写 `UNKNOWN`、`NOT_COMPUTED` 或“此传统规则下无法稳定判断”，不要用泛化语言填满章节。

默认输出采用“先人话总评、后专业证明”。简批先用一段口头话讲主线，再给最少必要依据；八字详批执行 `bazi-client-voice.md`，紫微详批执行 `ziwei-client-voice.md`，完成老师傅总断、现实核验与误差排查后再进入术语章节。八字客户正文不从四柱表、五行统计或格局名开头；紫微客户正文不从十二宫表、星曜组合或四化清单开头；两者都不要把每句话写成论文式标签。

第一层总评要有判断力但不能装神：用三至五条具体、可否证的行为机制抓住主线，每条同时写好处与代价；没有充分依据时说“这条我不硬断”。第二层再把每条总断映射到排盘事实、传统术语、规则 ID、反证、不确定度和现实建议。八字钩子来自旺衰、主线结构和岁运；紫微钩子来自命身张力、命财官迁联动、四化与大限。禁止万能性格话、单星直断、虚构经历、绝对化吉凶或恐吓。

默认输出以清楚、可核对为优先，不设强制字数。专业章节采用“人话小结 → 依据 → 行话解释 → 反证/限制 → 现实核验 → 低风险建议”，避免重复同一断语。

## 预注册与经历核对

只有用户明确要做验证时才启用：

1. 在读取用户经历前锁定原局判断、竞争假设、判别窗口和推翻条件。
2. 用户已提前提供经历时，标注“非盲测，存在信息污染”，不得声称完成独立预注册。
3. 后验仅做“与先前文本是否一致”的四态记录：命中 / 部分命中 / 未命中 / 未知。
4. 单次主观经历不能证明命理有效；不得用后验结果升级为科学可信度。

## 双盘对照

双盘结果只做**叙述一致性比较**。不得使用“可信度倍增”“验证出生时辰”“证明预测正确”等表述。两套体系共享出生输入且由同一模型解释，不构成独立证据。

对照海报使用 [references/report-schema.md](references/report-schema.md) 的结构化 schema。每项紫微依据必须指向实际宫位和星曜；生成前运行：

```bash
python -X utf8 scripts/validate_analysis.py --chart chart.json --analysis analysis.json
python -X utf8 scripts/make_poster.py --chart chart.json --analysis analysis.json --output report.html
```

## 安全与隐私

- 开头或首个实质段落说明“传统文化解释，仅供自我反思与娱乐参考”。
- 健康内容只可描述传统象征，不诊断疾病；有症状时建议咨询合格医务人员。
- 财运内容不提供买卖、借贷、辞职或投资指令；婚姻内容不替用户决定结婚、离婚或生育。
- 对未成年人只做文化介绍和非决定性的性格反思，不预测婚姻、财富、疾病或灾祸。
- 出生日期、时间、地点和性别参数属于敏感个人资料。生成分享页前提醒用户脱敏，并不主动扩散或持久保存。
- 用户决定分享结构化命盘时，可运行 `python -X utf8 scripts/redact_chart.py --chart chart.json --output share-chart.json`；该工具只移除直接身份字段，不得声称完成匿名化。
- 不预测生死、灾祸日期、违法风险或绝对结局；不使用“必然、注定、一定会”等措辞。

结尾自然提醒：命理为传统解释系统，供参照，非定数；现实决定应基于事实、专业意见与用户自主判断。
