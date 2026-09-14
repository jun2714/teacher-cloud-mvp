export async function downloadBlob(response, filename) {
  const data = response?.data
  if (data instanceof Blob && data.type && data.type.includes('application/json')) {
    const text = await data.text()
    let detail = '导出失败'
    try {
      const parsed = JSON.parse(text)
      if (parsed.detail) detail = parsed.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  const blob = data instanceof Blob ? data : new Blob([data])
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}
