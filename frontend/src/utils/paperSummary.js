export const SUM_SECTIONS = [
  { key: 'core', title: '核心' },
  { key: 'problem', title: '研究问题' },
  { key: 'method', title: '方法创新' },
  { key: 'result', title: '主要结果' },
  { key: 'limit', title: '结论与局限' },
  { key: 'insight', title: '领域启发' },
]

export function asBi(val) {
  if (val == null || val === '') return { zh: '', en: '' }
  if (typeof val === 'string') return { zh: val, en: '' }
  if (Array.isArray(val)) {
    const items = val.map((x) => (typeof x === 'string' ? { zh: x, en: '' } : asBi(x)))
      .filter((x) => x.zh || x.en)
    return {
      items,
      zh: items.map((x) => x.zh).filter(Boolean).join('\n'),
      en: items.map((x) => x.en).filter(Boolean).join('\n'),
    }
  }
  if (typeof val === 'object') {
    const zh = val.zh ?? val.zh_CN ?? val.chinese ?? ''
    const en = val.en ?? val.en_US ?? val.english ?? ''
    if (Array.isArray(zh) || Array.isArray(en)) {
      const zArr = Array.isArray(zh) ? zh : (zh ? [zh] : [])
      const eArr = Array.isArray(en) ? en : (en ? [en] : [])
      const n = Math.max(zArr.length, eArr.length)
      const items = Array.from({ length: n }, (_, i) => ({
        zh: String(zArr[i] || ''),
        en: String(eArr[i] || ''),
      })).filter((x) => x.zh || x.en)
      return {
        items,
        zh: items.map((x) => x.zh).filter(Boolean).join('\n'),
        en: items.map((x) => x.en).filter(Boolean).join('\n'),
      }
    }
    if (zh || en) return { zh: String(zh), en: String(en) }
    return { zh: '', en: '' }
  }
  return { zh: String(val), en: '' }
}

export function buildSummaryView(sm) {
  if (!sm) return null
  if (typeof sm === 'string') {
    const t = sm.trim()
    return t ? { sections: [{ key: 'core', title: '核心', zh: t, en: '' }], glossary: [] } : null
  }
  if (typeof sm !== 'object') return null
  const sections = SUM_SECTIONS.map((s) => ({ ...s, ...asBi(sm[s.key]) }))
    .filter((s) => s.zh || s.en || s.items?.length)
  const glossary = (sm.glossary || []).filter((g) => g && (g.en || g.zh))
  if (!sections.length && !glossary.length) return null
  return { sections, glossary }
}
