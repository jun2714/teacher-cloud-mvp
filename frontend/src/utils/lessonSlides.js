// One layout model drives both the browser presentation and editable PowerPoint.
import { LESSON_TEMPLATES } from './lessonTemplates.js'
export { DEFAULT_LESSON_THEME } from './lessonTemplates.js'
export const PROGRAM_NAME = '吴忠中学教师跟岗实践暨“县中帮扶”交流培训'
export const SLIDE_WIDTH = 1280
export const SLIDE_HEIGHT = 720
export const SLIDE_THEMES = [
  ...LESSON_TEMPLATES,
  { id: 'blue', name: '经典蓝', background: 'F5F7FB', ink: '172C4C', accent: '285EA8', muted: '56657B', cover: '172C4C', coverInk: 'FFFFFF', coverMuted: 'C9D9EF' },
  { id: 'green', name: '青竹绿', background: 'F5F8F4', ink: '173E33', accent: '326F59', muted: '526B61', cover: '173E33', coverInk: 'FFFFFF', coverMuted: 'D3E8DC' },
  { id: 'paper', name: '暖杏白', background: 'FBF6EE', ink: '49382B', accent: '99562E', muted: '75614E', cover: 'F1E5D3', coverInk: '49382B', coverMuted: '755B43' },
]

export function plainText(value) {
  return String(value || '')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '图片：$1（$2）')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1（$2）')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/(?<![\w*\\])\*([^\s*](?:[^*\n]*?[^\s*])?)\*(?!\*)/g, '$1')
    .replace(/(?<![\w\\])__([^_\n]+)__(?!\w)/g, '$1')
    .replace(/(?<![\w_\\])_([^\s_](?:[^_\n]*?[^\s_])?)_(?!\w)/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\u2028/g, '\n')
    .replace(/^\s*>\s?/gm, '')
    .trim()
}

// A conservative width estimate keeps lines inside their box across common CJK fonts.
export function wrapText(text, width, fontSize) {
  const lines = []
  for (const paragraph of String(text).split('\n')) {
    let line = '', used = 0
    for (const char of Array.from(paragraph)) {
      const units = /[\u0020-\u007e]/.test(char) ? (/[MW@%]/.test(char) ? 0.95 : 0.64) : 1.05
      if (line && used + units * fontSize > width) {
        lines.push(line)
        line = ''
        used = 0
      }
      line += char
      used += units * fontSize
    }
    lines.push(line)
  }
  return lines
}

function cells(line) {
  return line.trim().replace(/^\|/, '').replace(/(?<!\\)\|$/, '')
    .split(/(?<!\\)\|/).map((cell) => plainText(cell.replace(/\\\|/g, '|')))
}

function separator(line) {
  const row = cells(line)
  return row.length > 0 && row.every((cell) => /^:?-{2,}:?$/.test(cell.replace(/\s/g, '')))
}

export function parseLesson(content) {
  const lines = String(content || '').replace(/\r/g, '').split('\n')
  let heading = '', section = { title: '基本信息', blocks: [] }
  const sections = [section]
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    const fence = line.match(/^(`{3,}|~{3,})/)
    if (fence) {
      const code = []
      const closing = new RegExp('^' + fence[1][0] + '{' + fence[1].length + ',}\\s*$')
      while (++i < lines.length && !closing.test(lines[i].trim())) code.push(lines[i].replace(/\t/g, '    ').trimEnd())
      while (code.length && !code[0].trim()) code.shift()
      while (code.length && !code.at(-1).trim()) code.pop()
      const indent = Math.min(...code.filter((row) => row.trim()).map((row) => row.match(/^ */)[0].length))
      if (code.length) section.blocks.push({ text: code.map((row) => row.slice(indent)).join('\n'), preformatted: true })
      continue
    }
    if (!line || /^([-*_])\1{2,}$/.test(line)) continue
    const match = line.match(/^(#{1,6})\s+(.+)$/)
    if (match) {
      if (match[1] === '#' && !heading) { heading = plainText(match[2]); continue }
      if (match[1].length <= 2) {
        section = { title: plainText(match[2]), blocks: [] }
        sections.push(section)
      } else section.blocks.push({ text: plainText(match[2]), emphasis: true })
      continue
    }
    if (line.includes('|') && i + 1 < lines.length && separator(lines[i + 1])) {
      const headers = cells(line)
      i += 2
      let count = 0
      while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim()) {
        const row = cells(lines[i])
        section.blocks.push({
          tableRow: true,
          text: row.map((value, index) => (headers[index] || '补充内容') + '：' + value).join('\n'),
        })
        count++
        i++
      }
      if (!count) section.blocks.push({ text: headers.join(' / ') })
      i--
      continue
    }
    section.blocks.push({ text: plainText(line.replace(/^[-*]\s+/, '• ')), emphasis: false })
  }
  return { heading, sections: sections.filter((item) => item.blocks.length || item.title !== '基本信息') }
}

function element(text, x, y, w, h, size, role = 'ink', bold = false) {
  return { text, x, y, w, h, size, role, bold }
}

const metadataKeys = '教师姓名|授课教师|姓名|所在单位|工作单位|学校|学科|授课年级|年级|教材版本|课时安排|课题名称|指导教师|完成日期'
const metadataPattern = new RegExp('^(' + metadataKeys + ')\\s*[：:]\\s*(.*)$')
const sectionName = (text) => text.replace(/^[一二三四五六七八九十百\d]+[、.．）)]\s*/, '').trim()
const isReview = (text) => /^(?:指导教师|导师)(?:评语|评价|意见|签字|签名)(?:\s*[：:]|\s*$)/.test(sectionName(text))

// Presentation-only selection: the saved lesson and Word export keep the original text.
function presentationSections(parsed) {
  const metadata = new Map()
  const sections = []
  for (const section of parsed.sections) {
    if (isReview(section.title)) continue
    const intro = /^(基本信息|个人信息|教师信息|教学设计信息|教案信息)$/.test(sectionName(section.title))
    let reviewing = false
    const blocks = []
    for (const block of section.blocks) {
      if (isReview(block.text)) { reviewing = true; continue }
      if (reviewing) continue
      if (intro) {
        const remaining = block.text.split('\n').filter((line) => {
          const match = line.trim().match(metadataPattern)
          if (match) { metadata.set(match[1], match[2]); return false }
          return line !== PROGRAM_NAME && line !== parsed.heading
            && !/^说明[：:]\s*本表为跟岗期间/.test(line)
        })
        if (remaining.some((line) => line.trim())) blocks.push({ ...block, text: remaining.join('\n') })
      } else blocks.push(block)
    }
    if (blocks.length) sections.push({ ...section, blocks })
  }
  return { metadata, sections }
}

function coverDetails(metadata) {
  const value = (...keys) => {
    const text = keys.map((key) => metadata.get(key)).find(Boolean) || ''
    return /^(未提供|未填写|待填写|待定|暂无|无|[_—-]+)(?:\s|[（(]|$)/.test(text) ? '' : text.replace(/[（(]默认[^）)]*[）)]/g, '').trim()
  }
  const teacher = value('教师姓名', '授课教师', '姓名')
  const unit = value('所在单位', '工作单位', '学校')
  const mentor = value('指导教师')
  return [
    [teacher && '授课教师：' + teacher, mentor && '指导教师：' + mentor].filter(Boolean).join('    '),
    unit && '所在单位：' + unit,
    [value('学科'), value('授课年级', '年级'), value('课时安排'), value('完成日期')].filter(Boolean).join('  ·  '),
  ].filter(Boolean)
}

const BODY_BOTTOM = 627 // Leave clear space above the footer at y=657.
const lineHeight = (size) => size * 1.4
const rowHeight = (rows, size) => rows.length * lineHeight(size) + rows.slice(1).reduce((sum, row) => sum + (row.gap || 0), 0)
function blockRows(blocks, size) {
  return blocks.flatMap((block, index) => {
    const rows = []
    let gap = index ? 8 : 0
    for (const text of wrapText(block.text, 1112, size)) {
      // Board diagrams use blank lines to separate groups, not as full-height text.
      // Keep indentation and connecting arrows; only compact the empty space.
      if (block.preformatted && !text.trim()) { gap = Math.max(gap, size * 0.45); continue }
      rows.push({ text, bold: Boolean(block.emphasis), gap, blockStart: rows.length === 0 })
      gap = 0
    }
    return rows
  })
}

function paginateBlocks(blocks, height) {
  // Table rows are self-contained teaching stages; other blocks share the available space.
  const groups = []
  let group = []
  const flush = () => { if (group.length) { groups.push(group); group = [] } }
  for (const block of blocks) {
    if (block.tableRow) { flush(); groups.push([block]) }
    else group.push(block)
  }
  flush()
  return groups.flatMap((blocks) => {
    for (const size of [28, 26, 24]) {
      const rows = blockRows(blocks, size)
      if (rowHeight(rows, size) <= height) return [{ rows, size }]
    }
    const rows = blockRows(blocks, 28)
    const pages = []
    let start = 0
    while (start < rows.length) {
      let end = start + 1
      while (end < rows.length && rowHeight(rows.slice(start, end + 1), 28) <= height) end++
      // Keep a short paragraph together when it fits on the following page.
      if (end < rows.length && !rows[end].blockStart) {
        let boundary = end - 1
        while (boundary > start && !rows[boundary].blockStart) boundary--
        let next = end
        while (next < rows.length && !rows[next].blockStart) next++
        if (boundary > start && rowHeight(rows.slice(boundary, next), 28) <= height) end = boundary
      }
      pages.push({ rows: rows.slice(start, end), size: 28 })
      start = end
    }
    // A tiny continuation should merge with the previous page or share its content evenly.
    if (pages.length > 1) {
      const tail = pages.at(-1), previous = pages.at(-2)
      if (tail.rows.length <= 2 || tail.rows.map((row) => row.text.trim()).join('').length < 40) {
        const combined = [...previous.rows, ...tail.rows]
        const mergedSize = [26, 24].find((size) => rowHeight(combined, size) <= height)
        if (mergedSize) pages.splice(-2, 2, { rows: combined, size: mergedSize })
        else {
          let split = Math.ceil(combined.length / 2)
          const fits = (index) => rowHeight(combined.slice(0, index), 28) <= height && rowHeight(combined.slice(index), 28) <= height
          // Prefer a paragraph boundary near the middle if both pages still fit.
          const boundary = combined.findIndex((row, index) => index >= 3 && index <= combined.length - 3 && Math.abs(index - split) <= 2 && row.blockStart && fits(index))
          if (boundary !== -1) split = boundary
          if (fits(split)) pages.splice(-2, 2, { rows: combined.slice(0, split), size: 28 }, { rows: combined.slice(split), size: 28 })
        }
      }
    }
    return pages
  })
}

export function buildLessonSlides(content, { title = '个人教学设计', topic = '', themeId = 'blue' } = {}) {
  if (!String(content || '').trim()) return []
  const parsed = parseLesson(content)
  const { metadata, sections } = presentationSections(parsed)
  const metadataTopic = metadata.get('课题名称')
  const mainTitle = plainText(topic || metadataTopic || title || parsed.heading)
  const slides = []
  const theme = SLIDE_THEMES.find((item) => item.id === themeId) || SLIDE_THEMES.find((item) => item.id === 'blue')
  const cover = theme.coverLayout || { x: 84, width: 1112, programY: 76, labelY: 167, titleY: 243, detailsY: 488, detailsSize: 24 }
  const detailLines = coverDetails(metadata).flatMap((text) => wrapText(text, cover.width, cover.detailsSize))
  // Reserve a bounded cover area for useful personal information.
  const visibleDetails = detailLines.slice(0, 4)
  if (detailLines.length > 4) visibleDetails[3] = visibleDetails[3].slice(0, -1) + '…'
  const titleHeight = cover.titleHeight || (visibleDetails.length ? 220 : 320)
  let coverSize = 62
  while (coverSize > 26 && wrapText(mainTitle, cover.width, coverSize).length * coverSize * 1.3 > titleHeight) coverSize -= 2
  const coverLines = wrapText(mainTitle, cover.width, coverSize)
  const coverCapacity = Math.floor(titleHeight / (coverSize * 1.3))
  const titlePages = []
  for (let i = 0; i < coverLines.length; i += coverCapacity) titlePages.push(coverLines.slice(i, i + coverCapacity))
  for (const [index, titleLines] of titlePages.entries()) {
    slides.push({
      kind: 'cover', title: index ? '课题名称（续）' : '封面', section: '个人教学设计',
      notes: mainTitle,
      elements: [
        ...wrapText(PROGRAM_NAME, cover.width, theme.coverLayout ? 22 : 24).map((text, line) => element(text, cover.x, cover.programY + line * 30, cover.width, 30, theme.coverLayout ? 22 : 24, 'coverMuted')),
        element('个人教学设计' + (index ? ' · 续页' : ''), cover.x, cover.labelY, cover.width, 42, 30, 'coverMuted'),
        ...titleLines.map((text, line) => element(text, cover.x, cover.titleY + line * coverSize * 1.3, cover.width, coverSize * 1.3, coverSize, 'coverInk', true)),
        ...(index ? [] : visibleDetails.map((text, line) => element(text, cover.x, cover.detailsY + line * 32, cover.width, 32, cover.detailsSize, 'coverMuted'))),
      ].map((box) => ({ ...box, align: cover.align || 'left' })),
    })
  }
  for (const [sectionIndex, section] of sections.entries()) {
    const titleWidth = theme.contentImage ? 960 : 1112
    const titleLines = wrapText(section.title, titleWidth, 40)
    const shortTitle = titleLines.slice(0, 2)
    if (titleLines.length > 2) shortTitle[1] = shortTitle[1].slice(0, -1) + '…'
    const blocks = titleLines.length > 2 ? [{ text: section.title, emphasis: true }, ...section.blocks] : section.blocks
    const bodyY = theme.contentImage ? 185 : 237
    const pages = paginateBlocks(blocks, BODY_BOTTOM - bodyY)
    for (const [index, { rows, size }] of pages.entries()) {
      let y = bodyY
      const body = rows.map((row, line) => {
        if (line) y += row.gap || 0
        const box = { ...element(row.text, 84, y, 1112, lineHeight(size), size, row.bold ? 'accent' : 'ink', row.bold), body: true }
        y += lineHeight(size)
        return box
      })
      slides.push({
        kind: 'content', section: section.title,
        title: section.title + (pages.length > 1 ? '（' + (index + 1) + '/' + pages.length + '）' : ''),
        notes: rows.map((row) => row.text).join('\n'),
        elements: [
          ...(theme.contentImage ? [] : [element(String(sectionIndex + 1).padStart(2, '0') + '  /  个人教学设计', 84, 48, 1000, 32, 20, 'accent', true)]),
          ...shortTitle.map((text, line) => element(text, 84, (theme.contentImage ? 44 : 103) + line * 51, titleWidth, 54, 40, theme.contentImage ? 'accent' : 'ink', true)),
          ...body,
        ],
      })
    }
  }
  for (const [index, slide] of slides.entries()) {
    slide.themeId = theme.id
    slide.backgroundImage = slide.kind === 'cover' ? theme.coverImage : theme.contentImage
    if (slide.kind === 'cover' && theme.coverImage) continue
    const role = slide.kind === 'cover' ? 'coverMuted' : 'muted'
    slide.elements.push(element('教学设计汇报', 84, 657, 950, 28, 18, role))
    slide.elements.push(element(String(index + 1).padStart(2, '0') + ' / ' + slides.length, 1080, 657, 120, 28, 18, role))
  }
  return slides
}
