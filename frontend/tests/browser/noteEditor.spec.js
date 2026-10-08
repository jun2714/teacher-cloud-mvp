import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('access_token', 'test-token'))
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (!path.startsWith('/api/')) return route.continue()
    const json = path === '/api/me/' ? { id: 1, username: 'test', profile: { subject: '数学', grade: '高一' } }
      : path.includes('notices') ? { count: 0, results: [] } : []
    await route.fulfill({ json })
  })
})

test('record, transcribe, correct, save and reopen a note', async ({ page }) => {
  const note = { id: 7, title: '录音笔记', content: '核对后的语音正文', input_method: 'voice', tags: ['听课', '反思'], category: 'reflection' }
  await page.route('**/api/asr/transcribe/', async (route) => {
    expect(route.request().postDataBuffer().length).toBeGreaterThan(200)
    await route.fulfill({ json: { text: '今天观察学生讨论。' } })
  })
  await page.route('**/api/notes/', (route) => route.fulfill({ json: route.request().method() === 'POST' ? note : [note] }))
  await page.route('**/api/notes/7/', (route) => route.fulfill({ json: note }))
  await page.goto('/notes/new')
  await page.getByRole('button', { name: '语音录入', exact: true }).click()
  await page.getByRole('textbox', { name: '笔记标题' }).fill(note.title)
  await page.getByRole('textbox', { name: '笔记内容' }).fill('老师原有记录')
  await page.getByRole('button', { name: '开始录音' }).click()
  await expect(page.getByRole('timer')).toContainText('00:02')
  await expect(page.getByRole('button', { name: '文件上传', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: '请先停止录音' })).toBeDisabled()
  await page.getByRole('button', { name: '停止并转写' }).click()
  await expect(page.getByRole('textbox', { name: '笔记内容' })).toHaveValue(/老师原有记录[\s\S]*今天观察学生讨论/)
  await page.getByRole('textbox', { name: '笔记内容' }).fill(note.content)
  await page.getByRole('textbox', { name: '标签' }).fill('听课，反思')
  const request = page.waitForRequest((r) => r.url().endsWith('/api/notes/') && r.method() === 'POST')
  await page.getByRole('button', { name: '保存笔记', exact: true }).click()
  const body = (await request).postDataBuffer().toString('utf8')
  expect(body).toContain('核对后的语音正文')
  expect(body).toContain('audio_file')
  expect(body).not.toContain('今天观察学生讨论')
  await expect(page).toHaveURL(/\/notes$/)
  await page.getByRole('heading', { name: note.title }).click()
  await expect(page.getByRole('textbox', { name: '笔记内容' })).toHaveValue(note.content)
  await expect(page.getByRole('textbox', { name: '标签' })).toHaveValue('听课，反思')
})

test('audio upload failure can retry without duplicate text', async ({ page }) => {
  let calls = 0
  await page.route('**/api/asr/transcribe/', (route) => {
    calls++
    return route.fulfill(calls === 1 ? { status: 502, json: { detail: '语音服务暂时不可用' } } : { json: { text: '转写成功的内容' } })
  })
  await page.goto('/notes/new')
  await page.getByRole('button', { name: '语音录入', exact: true }).click()
  await page.getByRole('textbox', { name: '笔记内容' }).fill('保留的手动内容')
  await page.locator('input[type=file]').setInputFiles({ name: 'lesson.wav', mimeType: 'audio/wav', buffer: Buffer.from('audio') })
  await expect(page.getByRole('alert')).toContainText('语音服务暂时不可用')
  await expect(page.getByRole('textbox', { name: '笔记内容' })).toHaveValue('保留的手动内容')
  await page.getByRole('button', { name: '重试转写' }).click()
  await expect(page.getByRole('textbox', { name: '笔记内容' })).toHaveValue(/保留的手动内容[\s\S]*转写成功的内容/)
  expect((await page.getByRole('textbox', { name: '笔记内容' }).inputValue()).match(/转写成功的内容/g)).toHaveLength(1)
})

test('document extraction saves corrected content and original excerpt separately', async ({ page }) => {
  await page.route('**/api/notes/extract/', (route) => route.fulfill({ json: { filename: '教案.docx', excerpt: '识别出的原文', warnings: [] } }))
  await page.route('**/api/notes/', (route) => route.fulfill({ json: route.request().method() === 'POST' ? { id: 2 } : [] }))
  await page.goto('/notes/new')
  await page.getByRole('button', { name: '文件上传', exact: true }).click()
  await page.getByRole('textbox', { name: '笔记标题' }).fill('文档笔记')
  await page.locator('input[type=file]').setInputFiles({ name: '教案.docx', mimeType: 'application/octet-stream', buffer: Buffer.from('document') })
  await expect(page.getByRole('textbox', { name: '笔记内容' })).toHaveValue(/识别出的原文/)
  await page.getByRole('textbox', { name: '笔记内容' }).fill('老师修正后的正文')
  const request = page.waitForRequest((r) => r.url().endsWith('/api/notes/') && r.method() === 'POST')
  await page.getByRole('button', { name: '保存笔记', exact: true }).click()
  const body = (await request).postData()
  expect(body).toContain('老师修正后的正文')
  expect(body).toContain('raw_text')
  expect(body).toContain('识别出的原文')
  await expect(page).toHaveURL(/\/notes$/)
})

test('editing and deleting an existing note', async ({ page }) => {
  const note = { id: 8, title: '既有笔记', content: '原有正文', tags: [], input_method: 'text', category: 'reflection' }
  await page.route('**/api/notes/8/', (route) => {
    if (route.request().method() === 'DELETE') return route.fulfill({ status: 204 })
    return route.fulfill({ json: note })
  })
  await page.goto('/notes/8')
  await expect(page.getByRole('textbox', { name: '笔记内容' })).toHaveValue('原有正文')
  await page.getByRole('textbox', { name: '笔记内容' }).fill('修改的正文')
  const request = page.waitForRequest((r) => r.method() === 'PATCH' && r.url().endsWith('/api/notes/8/'))
  await page.getByRole('button', { name: '保存修改' }).click()
  expect((await request).postData()).toContain('修改的正文')
  await expect(page).toHaveURL(/\/notes$/)
  await page.goto('/notes/8')
  await page.getByRole('button', { name: '删除笔记' }).click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await expect(page).toHaveURL(/\/notes$/)
})

test('microphone denial leaves manual entry usable on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.addInitScript(() => { navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('denied', 'NotAllowedError') } })
  await page.goto('/notes/new')
  await page.getByRole('button', { name: '语音录入', exact: true }).click()
  await page.getByRole('button', { name: '开始录音' }).click()
  await expect(page.getByRole('alert')).toContainText('未获得麦克风权限')
  await expect(page.getByRole('button', { name: '手动输入', exact: true })).toBeEnabled()
  await expect(page.getByRole('textbox', { name: '笔记内容' })).toBeEnabled()
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false)
  await page.screenshot({ path: 'test-results/note-voice-mobile.png', fullPage: true, animations: 'disabled' })
})
