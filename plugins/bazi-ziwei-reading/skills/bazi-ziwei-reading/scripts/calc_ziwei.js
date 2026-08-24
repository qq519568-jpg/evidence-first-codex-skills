// calc_ziwei.js —— 紫微斗数排盘桥（Node + npm iztro）
// 用法: node calc_ziwei.js <YYYY-MM-DD> <timeIndex> <男|女>
// timeIndex: 0早子 1丑 2寅 3卯 4辰 5巳 6午 7未 8申 9酉 10戌 11亥 12晚子
import { astro } from 'iztro';
import { readFileSync } from 'node:fs';

let iztroVersion = 'UNKNOWN';
try {
  const packageJson = JSON.parse(readFileSync(new URL('./node_modules/iztro/package.json', import.meta.url), 'utf8'));
  iztroVersion = packageJson.version || 'UNKNOWN';
} catch {
  // Calculation can continue; the caller will see an explicit UNKNOWN version.
}

const [date, timeIndexStr, sex] = process.argv.slice(2);
const timeIndex = Number(timeIndexStr);
const gender = sex === '男' ? 'male' : 'female';
const fixLeap = true;

const r = astro.bySolar(date, timeIndex, gender, fixLeap);

const palaces = r.palaces.map((p) => ({
  宫: p.name,
  宫干支: `${p.heavenlyStem}${p.earthlyBranch}`,
  主星: (p.majorStars || []).map((s) => ({
    星: s.name,
    亮度: s.brightness || '',
    四化: s.mutagen || '',
  })),
  辅星: (p.minorStars || []).map((s) => s.name),
  杂曜: (p.adjectiveStars || []).map((s) => s.name),
  大限: p.decadal ? `${p.decadal.range[0]}-${p.decadal.range[1]}虚岁` : '',
}));

const sihua = [];
for (const p of r.palaces) {
  for (const s of p.majorStars || []) {
    if (s.mutagen) {
      sihua.push(`生年${s.mutagen}：${s.name} → ${p.name}宫(${p.earthlyBranch})`);
    }
  }
}

const out = {
  _meta: {
    引擎: 'iztro',
    版本: iztroVersion,
    流年数据: 'NOT_COMPUTED',
  },
  命宫: r.earthlyBranchOfSoulPalace,
  身宫: r.earthlyBranchOfBodyPalace,
  命主: r.soul,
  身主: r.body,
  五行局: r.fiveElementsClass,
  生肖: r.zodiac,
  星座: r.sign,
  农历: r.lunarDate,
  生年四化: sihua,
  十二宫: palaces,
};

process.stdout.write(JSON.stringify(out, null, 2));
