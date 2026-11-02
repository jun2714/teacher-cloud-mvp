<script setup>
import { computed } from 'vue'

const props = defineProps({ content: { type: String, default: '' } })

function stripRequiredMarks(text) {
  return String(text || '')
    .replace(/[＊∗﹡]/g, '*')
    .replace(/\*\*([^*\n]+?)\*\*\s*\*+\s*(?=[：:])/g, '**$1**')
    .replace(/(^|[^*\n])\*([^*\n]{1,24})\*(?=\s*[：:])/g, '$1$2')
    .replace(/([\u4e00-\u9fffA-Za-z0-9])\*(?=[：:])/g, '$1')
    .replace(/^(\s*(?:\d+[.、]\s*)?[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9/（）()]{0,30})\*+\s*$/gm, '$1')
    .replace(/<br\s*\/?>/gi, '\u2028')
    .replace(/^[ \t]*(?:\u2028)+[ \t]*$/gm, '')
    .replace(/^[ \t]*(?:\.{3,}|…{1,}|·{3,}|。{3,})[ \t]*$/gm, '')
    .replace(/^[ \t]*([-*_])\1{2,}[ \t]*$/gm, '')
}

// 与后端 services/text_clean.py 的 INTERNAL_FIELD_LABELS 保持一致。
const FIELD_LABELS = {
  transcript: '材料正文', material_kind: '材料类型', material_sources: '材料来源', course_teacher: '授课教师',
  student_context: '学情说明', teacher_name: '教师姓名', school_name: '所在单位', class_hours: '课时安排',
  complete_date: '完成日期', training_period: '跟岗时间', training_base: '跟岗基地', report_date: '报告日期',
  report_type: '报告类型', report_title: '报告标题', file_excerpt: '文件内容', file_name: '文件名',
  program_name: '项目名称', payload: '所提供材料',
}
const FIELD_KEYS = Object.keys(FIELD_LABELS).sort((a, b) => b.length - a.length).join('|')
const JSON_FIELD_PHRASE = new RegExp(
  '(?:所?提供的|输入的?|原始的?)?\\s*JSON\\s*(?:数据|资料|格式|对象|文件)?\\s*(?:中的?|里的?|的)?\\s*`?(?:' + FIELD_KEYS + ')`?\\s*字段(?:的)?(?:内容|文本|数据)?(?:中|里)?', 'g')
const JSON_ONLY_PHRASE = /(?:所?提供的|输入的?|原始的?|以下|上述)\s*JSON\s*(?:数据|资料|格式|对象|内容)?(?:中|里)?/g
const BACKTICK_FIELD = new RegExp('`(' + FIELD_KEYS + ')`\\s*(?:字段)?', 'g')
const BARE_FIELD = new RegExp('(?<![A-Za-z_])(' + FIELD_KEYS + ')(?![A-Za-z_])\\s*字段', 'g')

function stripInternalTerms(text) {
  return text
    .replace(JSON_FIELD_PHRASE, '所提供材料')
    .replace(JSON_ONLY_PHRASE, '所提供材料')
    .replace(BACKTICK_FIELD, (_, key) => FIELD_LABELS[key])
    .replace(BARE_FIELD, (_, key) => FIELD_LABELS[key])
    .replaceAll('所提供的所提供材料', '所提供材料')
    .replaceAll('提供的所提供材料', '所提供材料')
}

function escapeHtml(s) {
  return s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

function inline(s) {
  return escapeHtml(s)
    .replace(/\u2028/g, '<br>')
    .replace(/`([^`\n]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(?<![\w*\\])\*([^\s*](?:[^*\n]*?[^\s*])?)\*(?!\*)/g, '<em>$1</em>')
}

function splitCells(line) {
  let s = line.trim()
  if (s.startsWith('|')) s = s.slice(1)
  if (s.endsWith('|')) s = s.slice(0, -1)
  return s.split('|').map((c) => c.trim())
}

function isSepRow(line) {
  const cells = splitCells(line)
  return cells.length > 0 && cells.every((c) => {
    const t = c.replace(/\s/g, '')
    return !t || /^:?-{2,}:?$/.test(t)
  })
}

function tableHtml(lines) {
  const rows = []
  for (const line of lines) {
    if (isSepRow(line)) continue
    rows.push(splitCells(line))
  }
  if (!rows.length) return ''
  const [head, ...body] = rows
  const th = head.map((c) => `<th>${inline(c)}</th>`).join('')
  const trs = body.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`).join('')
  return `<div class="markdown-table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div>`
}

const html = computed(() => {
  // Parse fences before cleaning prose so board diagrams retain their symbols and spacing.
  const lines = stripInternalTerms(props.content || '').split(/\r?\n/)
  const out = []
  let i = 0
  let listBuf = []
  const flushList = () => {
    if (listBuf.length) {
      out.push(`<ul>${listBuf.join('')}</ul>`)
      listBuf = []
    }
  }
  while (i < lines.length) {
    const fence = lines[i].trim().match(/^(`{3,}|~{3,})/)
    if (fence) {
      flushList()
      const code = []
      const closing = new RegExp('^' + fence[1][0] + '{' + fence[1].length + ',}\\s*$')
      while (++i < lines.length && !closing.test(lines[i].trim())) code.push(lines[i])
      out.push(`<pre class="markdown-board"><code>${escapeHtml(code.join('\n'))}</code></pre>`)
      i += 1
      continue
    }
    const line = stripRequiredMarks(lines[i])
    if (line.trim().startsWith('|')) {
      flushList()
      const tableLines = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(stripRequiredMarks(lines[i]))
        i += 1
      }
      out.push(tableHtml(tableLines))
      continue
    }
    if (/^### /.test(line)) {
      flushList()
      out.push(`<h4>${inline(line.slice(4))}</h4>`)
    } else if (/^## /.test(line)) {
      flushList()
      out.push(`<h3>${inline(line.slice(3))}</h3>`)
    } else if (/^# /.test(line)) {
      flushList()
      out.push(`<h2>${inline(line.slice(2))}</h2>`)
    } else if (/^>\s*/.test(line)) {
      flushList()
      out.push(`<blockquote>${inline(line.replace(/^>\s*/, ''))}</blockquote>`)
    } else if (/^\s*[-*+]\s+/.test(line)) {
      listBuf.push(`<li>${inline(line.replace(/^\s*[-*+]\s+/, ''))}</li>`)
    } else if (!line.trim()) {
      flushList()
    } else {
      flushList()
      out.push(`<p>${inline(line)}</p>`)
    }
    i += 1
  }
  flushList()
  return out.join('')
})
</script>

<template>
  <div class="markdown" v-html="html"></div>
</template>
