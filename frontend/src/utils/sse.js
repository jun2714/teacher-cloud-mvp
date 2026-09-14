export async function postSse(url, payload, { onEvent, signal } = {}) {
  const token = localStorage.getItem('access_token')
  const isForm = typeof FormData !== 'undefined' && payload instanceof FormData
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      ...(isForm ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: isForm ? payload : JSON.stringify(payload),
    signal,
  })

  if (!response.ok) {
    let detail = `请求失败（${response.status}）`
    try {
      const data = await response.json()
      if (typeof data?.detail === 'string') detail = data.detail
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }

  if (!response.body) {
    throw new Error('当前浏览器不支持流式输出')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''
    for (const part of parts) {
      const line = part.split('\n').find((row) => row.startsWith('data:'))
      if (!line) continue
      const raw = line.slice(5).trim()
      if (!raw || raw === '[DONE]') continue
      try {
        onEvent?.(JSON.parse(raw))
      } catch {
        /* ignore malformed chunk */
      }
    }
  }
}
