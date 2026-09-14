<script setup>
import { computed } from 'vue'

const props = defineProps({ content: { type: String, default: '' } })

function stripRequiredMarks(text) {
  return String(text || '')
    .replace(/\*\*([^*\n]+?)\*\*\*/g, '**$1**')
    .replace(/([\u4e00-\u9fff])\*([：:])/g, '$1$2')
    .replace(/^(\s*(?:\d+[\.、]\s*)?[\u4e00-\u9fff][\u4e00-\u9fffA-Za-z0-9/]*)\*\s*$/gm, '$1')
}

function escapeHtml(s) {
  return s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
}

function inline(s) {
  return s
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
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
  const lines = escapeHtml(stripRequiredMarks(props.content)).split(/\r?\n/)
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
    const line = lines[i]
    if (line.trim().startsWith('|')) {
      flushList()
      const tableLines = []
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i])
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
    } else if (/^> /.test(line)) {
      flushList()
      out.push(`<blockquote>${inline(line.slice(2))}</blockquote>`)
    } else if (/^[-*] /.test(line)) {
      listBuf.push(`<li>${inline(line.slice(2))}</li>`)
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
