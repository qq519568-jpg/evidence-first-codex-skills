#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双盘排算脚本：一次计算八字四柱（含十神、藏干、刑冲合害、空亡、纳音、大运）
与紫微斗数命盘（十二宫星曜、四化、大限），输出结构化 JSON 供解盘使用。

依赖（2026-08-14 换引擎，脱离 MSVC 编译依赖）：
  八字：lunar_python（纯 Python，wheel 直装）   pip install lunar_python
  紫微：Node >= 18 + npm iztro（先运行 setup_dependencies.ps1）
        python bridge 调 node scripts/calc_ziwei.js
  旧依赖 sxtwl / py-iztro(pythonmonkey) 在无 MSVC 环境编译失败，已弃用。

用法：
  python calc_chart.py --date 2000-01-01 --time 12:30 --sex 男
  python calc_chart.py --date 2000-01-01 --hour 12 --sex 男
  python calc_chart.py --date 2000-01-01 --time-index 6 --sex 男   # time-index 见下
  python calc_chart.py --date 2000-01-01 --time 12:30 --sex 男 --flow-year 2026 --flow-year 2027
  time-index: 0早子 1丑 2寅 3卯 4辰 5巳 6午 7未 8申 9酉 10戌 11亥 12晚子
"""
import argparse, json, sys, os, re, shutil, subprocess
from datetime import date as date_type
from importlib import metadata

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENDOR_DIR = os.path.join(SCRIPT_DIR, "vendor")
if os.path.isdir(VENDOR_DIR) and VENDOR_DIR not in sys.path:
    sys.path.insert(0, VENDOR_DIR)

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
WUXING_G = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
            "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
WUXING_Z = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
            "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
YINYANG = {"甲": 1, "丙": 1, "戊": 1, "庚": 1, "壬": 1, "乙": -1, "丁": -1, "己": -1, "辛": -1, "癸": -1}
CANGGAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"], "午": ["丁", "己"], "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"], "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}
NAYIN = {
    "甲子": "海中金", "乙丑": "海中金", "丙寅": "炉中火", "丁卯": "炉中火", "戊辰": "大林木", "己巳": "大林木",
    "庚午": "路旁土", "辛未": "路旁土", "壬申": "剑锋金", "癸酉": "剑锋金", "甲戌": "山头火", "乙亥": "山头火",
    "丙子": "涧下水", "丁丑": "涧下水", "戊寅": "城头土", "己卯": "城头土", "庚辰": "白蜡金", "辛巳": "白蜡金",
    "壬午": "杨柳木", "癸未": "杨柳木", "甲申": "泉中水", "乙酉": "泉中水", "丙戌": "屋上土", "丁亥": "屋上土",
    "戊子": "霹雳火", "己丑": "霹雳火", "庚寅": "松柏木", "辛卯": "松柏木", "壬辰": "长流水", "癸巳": "长流水",
    "甲午": "沙中金", "乙未": "沙中金", "丙申": "山下火", "丁酉": "山下火", "戊戌": "平地木", "己亥": "平地木",
    "庚子": "壁上土", "辛丑": "壁上土", "壬寅": "金箔金", "癸卯": "金箔金", "甲辰": "覆灯火", "乙巳": "覆灯火",
    "丙午": "天河水", "丁未": "天河水", "戊申": "大驿土", "己酉": "大驿土", "庚戌": "钗钏金", "辛亥": "钗钏金",
    "壬子": "桑柘木", "癸丑": "桑柘木", "甲寅": "大溪水", "乙卯": "大溪水", "丙辰": "沙中土", "丁巳": "沙中土",
    "戊午": "天上火", "己未": "天上火", "庚申": "石榴木", "辛酉": "石榴木", "壬戌": "大海水", "癸亥": "大海水",
}
LIUHE = {"子": "丑", "丑": "子", "寅": "亥", "亥": "寅", "卯": "戌", "戌": "卯",
         "辰": "酉", "酉": "辰", "巳": "申", "申": "巳", "午": "未", "未": "午"}
LIUCHONG = {"子": "午", "午": "子", "丑": "未", "未": "丑", "寅": "申", "申": "寅",
            "卯": "酉", "酉": "卯", "辰": "戌", "戌": "辰", "巳": "亥", "亥": "巳"}
LIUHAI = {"子": "未", "未": "子", "丑": "午", "午": "丑", "寅": "巳", "巳": "寅",
          "卯": "辰", "辰": "卯", "申": "亥", "亥": "申", "酉": "戌", "戌": "酉"}
XING = [("子", "卯"), ("丑", "戌"), ("戌", "未"), ("未", "丑"), ("寅", "巳"), ("巳", "申"), ("辰", "辰"), ("午", "午"), ("酉", "酉"), ("亥", "亥")]
SANHE = [("申", "子", "辰", "水"), ("寅", "午", "戌", "火"), ("巳", "酉", "丑", "金"), ("亥", "卯", "未", "木")]
TIANGAN_HE = {"甲": "己", "己": "甲", "乙": "庚", "庚": "乙", "丙": "辛", "辛": "丙", "丁": "壬", "壬": "丁", "戊": "癸", "癸": "戊"}
TIANGAN_CHONG = [("甲", "庚"), ("乙", "辛"), ("丙", "壬"), ("丁", "癸")]
GZ60 = [GAN[i % 10] + ZHI[i % 12] for i in range(60)]
PILLAR_POS = ["年", "月", "日", "时"]


def shishen(day_gan, other_gan):
    """以日干为日主，求另一天干的十神"""
    dw, ow = WUXING_G[day_gan], WUXING_G[other_gan]
    same_yy = YINYANG[day_gan] == YINYANG[other_gan]
    sheng = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}  # 我生
    ke = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}      # 我克
    if dw == ow:
        return "比肩" if same_yy else "劫财"
    if sheng[dw] == ow:
        return "食神" if same_yy else "伤官"
    if ke[dw] == ow:
        return "偏财" if same_yy else "正财"
    if ke[ow] == dw:
        return "七杀" if same_yy else "正官"
    return "偏印" if same_yy else "正印"


def package_version(*names):
    """Return an installed distribution version without making calculation depend on it."""
    for name in names:
        try:
            return metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return "UNKNOWN"


def find_relations(gans, zhis):
    rels = []
    pos = ["年", "月", "日", "时"]
    # 天干合冲
    for i in range(4):
        for j in range(i + 1, 4):
            if TIANGAN_HE.get(gans[i]) == gans[j]:
                rels.append(f"天干合：{pos[i]}{gans[i]}与{pos[j]}{gans[j]}相合")
            for a, b in TIANGAN_CHONG:
                if (gans[i], gans[j]) in [(a, b), (b, a)]:
                    rels.append(f"天干冲：{pos[i]}{gans[i]}与{pos[j]}{gans[j]}相冲")
    # 地支六冲六合六害相刑
    for i in range(4):
        for j in range(i + 1, 4):
            a, b = zhis[i], zhis[j]
            if LIUHE.get(a) == b:
                rels.append(f"六合：{pos[i]}{a}与{pos[j]}{b}相合")
            if LIUCHONG.get(a) == b:
                rels.append(f"六冲：{pos[i]}{a}与{pos[j]}{b}相冲")
            if LIUHAI.get(a) == b:
                rels.append(f"六害：{pos[i]}{a}与{pos[j]}{b}相害")
            if (a, b) in XING or (b, a) in XING:
                rels.append(f"相刑：{pos[i]}{a}与{pos[j]}{b}相刑")
    # 三合（含半合）
    zs = list(zhis)
    for a, b, c, wx in SANHE:
        have = [z for z in (a, b, c) if z in zs]
        if len(have) == 3:
            rels.append(f"三合{wx}局：{a}{b}{c}全")
        elif len(have) == 2:
            mid = b if b in have else None
            if mid or (a in have and c in have):
                rels.append(f"半合{wx}局：{'、'.join(have)}")
    return rels


def duration_from_minutes(minutes):
    """把分钟数保留为可审计原值，并提供无进位歧义的日时分拆分。"""
    days, remainder = divmod(minutes, 1440)
    hours, mins = divmod(remainder, 60)
    return {"总分钟": minutes, "日": days, "时": hours, "分": mins}


def parse_clock(value):
    """严格解析 HH:MM，避免 datetime 的宽松格式掩盖输入问题。"""
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", value or "")
    if not match:
        raise ValueError("--time 必须是 24 小时制 HH:MM（00:00-23:59）")
    return int(match.group(1)), int(match.group(2))


def jie_context(lunar, solar):
    """返回前后月令节（不是所有中气）及与出生民用时的分钟差。"""
    prev_jie = lunar.getPrevJie()
    next_jie = lunar.getNextJie()
    prev_solar = prev_jie.getSolar()
    next_solar = next_jie.getSolar()
    return {
        "上一节": {
            "名称": prev_jie.getName(),
            "公历时刻": prev_solar.toYmdHms(),
            "距出生": duration_from_minutes(solar.subtractMinute(prev_solar)),
        },
        "下一节": {
            "名称": next_jie.getName(),
            "公历时刻": next_solar.toYmdHms(),
            "距出生": duration_from_minutes(next_solar.subtractMinute(solar)),
        },
        "口径": "lunar_python 的前后月令节；分钟差忽略节气时刻中的秒数",
    }


def analysis_facts(day_gan, pillars, gans, zhis):
    """只整理可复核的结构事实，不自动给旺衰、格局或用神结论。"""
    groups = {"印比生扶": [], "食伤泄秀": [], "财星耗身": [], "官杀制身": []}
    group_by_ten_god = {
        "比肩": "印比生扶", "劫财": "印比生扶", "正印": "印比生扶", "偏印": "印比生扶",
        "食神": "食伤泄秀", "伤官": "食伤泄秀",
        "正财": "财星耗身", "偏财": "财星耗身",
        "正官": "官杀制身", "七杀": "官杀制身",
    }
    roots = []
    for pos, zhi in zip(PILLAR_POS, zhis):
        same_element_stems = [stem for stem in CANGGAN[zhi] if WUXING_G[stem] == WUXING_G[day_gan]]
        if same_element_stems:
            roots.append({"柱": pos, "地支": zhi, "同五行藏干": same_element_stems})
    for pos, gan in zip(PILLAR_POS, gans):
        god = "日主" if pos == "日" else shishen(day_gan, gan)
        if god in group_by_ten_god:
            groups[group_by_ten_god[god]].append({"位置": f"{pos}干", "干": gan, "十神": god})
    for pos, zhi in zip(PILLAR_POS, zhis):
        for stem in CANGGAN[zhi]:
            god = shishen(day_gan, stem)
            groups[group_by_ten_god[god]].append({"位置": f"{pos}支{zhi}藏干", "干": stem, "十神": god})
    return {
        "月令": {"地支": zhis[1], "本气五行": WUXING_Z[zhis[1]], "月柱": pillars[1]},
        "日主同五行藏干落点": roots,
        "十神作用分组": groups,
        "旺衰结论": "NOT_COMPUTED",
        "格局结论": "NOT_COMPUTED",
        "用神结论": "NOT_COMPUTED",
        "说明": "这些是供人工按规则注册表审查的定位事实，不是强弱分数。",
    }


def external_relations(flow_gz, natal_gans, natal_zhis, dayun_gz="", source_label="流年"):
    """列出外来干支（流年或大运）与原局/所在大运的机械关系。"""
    fg, fz = flow_gz[0], flow_gz[1]
    relations = []

    def add(kind, target, detail):
        item = {"类型": kind, "对象": target, "说明": detail}
        if item not in relations:
            relations.append(item)

    for pos, gan, zhi in zip(PILLAR_POS, natal_gans, natal_zhis):
        if TIANGAN_HE.get(fg) == gan:
            add("天干合", f"原局{pos}柱", f"{source_label}{fg}与{pos}干{gan}相合")
        if any((fg, gan) in ((a, b), (b, a)) for a, b in TIANGAN_CHONG):
            add("天干冲", f"原局{pos}柱", f"{source_label}{fg}与{pos}干{gan}相冲")
        if LIUHE.get(fz) == zhi:
            add("六合", f"原局{pos}柱", f"{source_label}{fz}与{pos}支{zhi}六合")
        if LIUCHONG.get(fz) == zhi:
            add("六冲", f"原局{pos}柱", f"{source_label}{fz}与{pos}支{zhi}六冲")
        if LIUHAI.get(fz) == zhi:
            add("六害", f"原局{pos}柱", f"{source_label}{fz}与{pos}支{zhi}相害")
        if (fz, zhi) in XING or (zhi, fz) in XING:
            add("相刑", f"原局{pos}柱", f"{source_label}{fz}与{pos}支{zhi}相刑")
        if flow_gz == gan + zhi:
            add("伏吟", f"原局{pos}柱", f"{source_label}{flow_gz}与{pos}柱同干支")
        stem_clash = any((fg, gan) in ((a, b), (b, a)) for a, b in TIANGAN_CHONG)
        if stem_clash and LIUCHONG.get(fz) == zhi:
            add("干支双冲", f"原局{pos}柱", f"{source_label}{flow_gz}与{pos}柱{gan}{zhi}天干、地支皆冲")

    for a, b, c, element in SANHE:
        triple = {a, b, c}
        present = triple.intersection(set(natal_zhis + [fz]))
        if triple.issubset(present) and fz in triple:
            add("三合全组", "原局地支", f"{source_label}{fz}与原局地支构成{a}{b}{c}三合{element}全组；是否成化未判")
        elif fz in triple and len(present) == 2:
            add("三合半合", "原局地支", f"{source_label}{fz}与原局地支构成{element}局两支组合；是否成化未判")

    if dayun_gz:
        dg, dz = dayun_gz[0], dayun_gz[1]
        if flow_gz == dayun_gz:
            add("岁运并临", "所在大运", f"流年与大运同为{flow_gz}")
        if TIANGAN_HE.get(fg) == dg:
            add("天干合", "所在大运", f"流年{fg}与大运干{dg}相合")
        if any((fg, dg) in ((a, b), (b, a)) for a, b in TIANGAN_CHONG):
            add("天干冲", "所在大运", f"流年{fg}与大运干{dg}相冲")
        if LIUHE.get(fz) == dz:
            add("六合", "所在大运", f"流年{fz}与大运支{dz}六合")
        if LIUCHONG.get(fz) == dz:
            add("六冲", "所在大运", f"流年{fz}与大运支{dz}六冲")
        if LIUHAI.get(fz) == dz:
            add("六害", "所在大运", f"流年{fz}与大运支{dz}相害")
        if (fz, dz) in XING or (dz, fz) in XING:
            add("相刑", "所在大运", f"流年{fz}与大运支{dz}相刑")
    return relations


def requested_flow_years(years, all_dayun, day_gan, natal_gans, natal_zhis):
    if not years:
        return {"状态": "NOT_COMPUTED", "请求年份": [], "结果": []}
    results = []
    for requested_year in sorted(set(years)):
        containing = next((d for d in all_dayun
                           if d.getStartYear() <= requested_year <= d.getEndYear()), None)
        if containing is None:
            first, last = all_dayun[0].getStartYear(), all_dayun[-1].getEndYear()
            raise ValueError(f"--flow-year {requested_year} 超出当前排运覆盖范围 {first}-{last}")
        liu_nian = next((ln for ln in containing.getLiuNian()
                         if ln.getYear() == requested_year), None)
        if liu_nian is None:
            raise ValueError(f"无法从固定引擎取得 {requested_year} 流年")
        flow_gz = liu_nian.getGanZhi()
        dayun_gz = containing.getGanZhi()
        dayun_info = ({"状态": "起运前", "运": ""} if containing.getIndex() == 0 else {
            "状态": "大运中",
            "运": dayun_gz,
            "公历年份范围": f"{containing.getStartYear()}–{containing.getEndYear()}",
            "起止虚岁": f"{containing.getStartAge()}–{containing.getEndAge()}",
        })
        results.append({
            "公历年": requested_year,
            "流年干支": flow_gz,
            "虚岁": liu_nian.getAge(),
            "流年十神": {
                "天干": shishen(day_gan, flow_gz[0]),
                "地支本气": shishen(day_gan, CANGGAN[flow_gz[1]][0]),
            },
            "所在大运": dayun_info,
            "作用关系": external_relations(flow_gz, natal_gans, natal_zhis, dayun_gz),
        })
    return {
        "状态": "COMPUTED",
        "请求年份": sorted(set(years)),
        "结果": results,
        "边界": "只输出干支、十神、大运归属及机械关系；不自动推出事件。交运年份需结合起运公历时刻细分。",
    }


def calc_bazi(year, month, day, hour, minute, sex, flow_years=None):
    """lunar_python 排八字。23:00 属晚子时（日柱当天），0:00 属早子时。"""
    from lunar_python import Solar
    solar = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()

    pillars = [ec.getYear(), ec.getMonth(), ec.getDay(), ec.getTime()]
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]
    day_gan = ec.getDayGan()

    pillars_info = []
    for name, gz, hide, shishen_gan, shishen_zhi in zip(
            ["年", "月", "日", "时"],
            pillars,
            [ec.getYearHideGan(), ec.getMonthHideGan(), ec.getDayHideGan(), ec.getTimeHideGan()],
            [ec.getYearShiShenGan(), ec.getMonthShiShenGan(), ec.getDayShiShenGan(), ec.getTimeShiShenGan()],
            [ec.getYearShiShenZhi(), ec.getMonthShiShenZhi(), ec.getDayShiShenZhi(), ec.getTimeShiShenZhi()]):
        # lunar 的十神以日主为基准；日柱天干十神标"日主"
        gs = "日主" if name == "日" else shishen_gan
        # 藏干十神：优先用 lunar 结果，长度异常时回退自算
        zs = shishen_zhi if len(shishen_zhi) == len(hide) else [shishen(day_gan, c) for c in hide]
        pillars_info.append({
            "柱": name, "干支": gz, "纳音": ec.getYearNaYin() if name == "年" else
            ec.getMonthNaYin() if name == "月" else
            ec.getDayNaYin() if name == "日" else ec.getTimeNaYin(),
            "天干十神": gs,
            "地支藏干": [{"干": c, "十神": s} for c, s in zip(hide, zs)],
        })

    # 五行统计（天干地支本气）
    wx_count = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for g in gans:
        wx_count[WUXING_G[g]] += 1
    for z in zhis:
        wx_count[WUXING_Z[z]] += 1

    # 大运：固定使用 lunar_python sect=1；内部按顺逆取前/后一个“节”。
    yun = ec.getYun(1 if sex == "男" else 0)
    forward = yun.isForward() if hasattr(yun, "isForward") else True
    all_dys = yun.getDaYun(12)
    dys = all_dys[1:9]                      # 对外默认展示八步，跳过“起运前”空项
    start_solar = yun.getStartSolar()
    start_age = dys[0].getStartAge()
    dayun = []
    for i, d in enumerate(dys[:8]):
        gz = d.getGanZhi()
        transition = start_solar.nextYear(i * 10)
        next_transition = start_solar.nextYear((i + 1) * 10)
        dayun.append({"运": gz,
                      "十神干": shishen(day_gan, gz[0]),
                      "十神支": shishen(day_gan, CANGGAN[gz[1]][0]),
                      "起止虚岁": f"{d.getStartAge()}–{d.getEndAge()}",
                      "公历年份范围": f"{d.getStartYear()}–{d.getEndYear()}",
                      "交运公历": transition.toYmdHms(),
                      "下次交运公历": next_transition.toYmdHms(),
                      "与原局作用关系": external_relations(gz, gans, zhis, source_label="大运")})

    chosen_jie = lunar.getNextJie() if forward else lunar.getPrevJie()
    chosen_minutes = (chosen_jie.getSolar().subtractMinute(solar) if forward
                      else solar.subtractMinute(chosen_jie.getSolar()))

    return {
        "四柱": pillars_info,
        "日主": day_gan,
        "日主五行": WUXING_G[day_gan],
        "五行统计": wx_count,
        "分析事实": analysis_facts(day_gan, pillars, gans, zhis),
        "空亡": ec.getDayXunKong(),
        "刑冲合害": find_relations(gans, zhis),
        "节气上下文": jie_context(lunar, solar),
        "大运方向": "顺行" if forward else "逆行",
        "起运虚岁": start_age,
        "起运": {
            "算法": "lunar_python Yun sect=1",
            "取节方向": "下一节" if forward else "上一节",
            "所取节令": chosen_jie.getName(),
            "距所取节令": duration_from_minutes(chosen_minutes),
            "起运时长": {
                "年": yun.getStartYear(), "月": yun.getStartMonth(),
                "日": yun.getStartDay(), "时": yun.getStartHour(),
            },
            "起运公历": start_solar.toYmdHms(),
            "起运虚岁": start_age,
            "说明": "起运时长与起运公历由固定引擎直接返回；虚岁取第一步大运的 startAge。",
        },
        "大运": dayun,
        "流年": requested_flow_years(flow_years or [], all_dys, day_gan, gans, zhis),
    }


def calc_ziwei(date_str, time_index, sex):
    """紫微：python 桥调 node scripts/calc_ziwei.js（npm iztro）。node 缺失时返回错误对象。"""
    script = os.path.join(SCRIPT_DIR, "calc_ziwei.js")
    if not shutil.which("node"):
        return {"错误": "未检测到 node，无法排紫微盘。请安装 Node >= 18 并在 scripts/ 目录执行 npm install。"}
    try:
        r = subprocess.run(
            ["node", script, date_str, str(time_index), sex],
            capture_output=True, timeout=60, encoding="utf-8")
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"错误": f"node 桥调用失败：{e}"}
    if r.returncode != 0:
        return {"错误": f"node 桥退出码 {r.returncode}：{r.stderr[:500]}"}
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"错误": f"node 桥输出非 JSON：{r.stdout[:300]}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="公历出生日期 YYYY-MM-DD")
    time_group = ap.add_mutually_exclusive_group(required=True)
    time_group.add_argument("--time", help="出生当地民用时间 HH:MM，推荐")
    time_group.add_argument("--hour", type=int, help="出生小时 0-23")
    time_group.add_argument("--time-index", type=int, help="时辰序号 0早子…12晚子")
    ap.add_argument("--sex", required=True, choices=["男", "女"])
    ap.add_argument("--place", default="UNKNOWN", help="出生地，仅记录，不执行经纬度换算")
    ap.add_argument("--timezone", default="UNKNOWN", help="IANA 时区或 UTC 偏移，仅记录，不自动换算")
    ap.add_argument("--flow-year", type=int, action="append", default=[],
                    help="按需计算一个公历流年，可重复；未提供时保持 NOT_COMPUTED")
    args = ap.parse_args()

    try:
        parsed_date = date_type.fromisoformat(args.date)
    except ValueError:
        ap.error("--date 必须是有效公历日期 YYYY-MM-DD")

    # 时辰序号：iztro 0=早子,1=丑,…,11=亥,12=晚子
    if args.time_index is not None:
        ti = args.time_index
        if not 0 <= ti <= 12:
            ap.error("--time-index 必须在 0-12")
        hour = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 23][ti]
        minute = 0
    elif args.time is not None:
        try:
            hour, minute = parse_clock(args.time)
        except ValueError as exc:
            ap.error(str(exc))
        ti = 0 if hour == 0 else (12 if hour == 23 else (hour + 1) // 2)
    else:
        h = args.hour
        if not 0 <= h <= 23:
            ap.error("--hour 必须在 0-23")
        ti = 0 if h == 0 else (12 if h == 23 else (h + 1) // 2)
        hour = h
        minute = 0

    for flow_year in args.flow_year:
        if not parsed_date.year <= flow_year <= parsed_date.year + 109:
            ap.error(f"--flow-year 必须在出生年到出生后 109 年之间：{parsed_date.year}-{parsed_date.year + 109}")

    y, m, dd = parsed_date.year, parsed_date.month, parsed_date.day
    out = {
        "_meta": {
            "schema_version": "2.2",
            "历法": "公历",
            "换日口径": "midnight（00:00 换日；23:00 仍按输入日期）",
            "八字引擎": {"名称": "lunar_python", "版本": package_version("lunar-python", "lunar_python")},
            "计算边界": [
                "出生地与时区仅记录，未执行经纬度、真太阳时或夏令时换算",
                "五行统计为天干与地支本气的未加权计数，不等于旺衰强度",
                "起运采用 lunar_python Yun sect=1；节气分钟差忽略节气时刻中的秒数",
                "流年只在 --flow-year 请求后计算，且只输出结构事实，不自动产生事件预测",
                "未计算紫微流年宫位与流年四化"
            ]
        },
        "输入": {
            "公历": args.date,
            "当地民用时间": f"{hour:02d}:{minute:02d}",
            "当地民用小时": hour,
            "当地民用分钟": minute,
            "时辰序号": ti,
            "性别参数": args.sex,
            "出生地": args.place,
            "时区": args.timezone
        },
        "八字": calc_bazi(y, m, dd, hour, minute, args.sex, args.flow_year),
        "紫微": calc_ziwei(args.date, ti, args.sex),
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
