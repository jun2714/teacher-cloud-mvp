import { test, expect } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('access_token', 'test-token'))
  await page.route('**/api/**', async (route) => {
    const url = route.request().url()
    if (!new URL(url).pathname.startsWith('/api/')) return route.continue()
    const json = url.endsWith('/me/') ? { id: 1, username: 'test', profile: { subject: '数学', grade: '高一' } }
      : url.includes('notices') ? { count: 0, results: [] } : {}
    await route.fulfill({ json })
  })
})

test('multiple materials preserve manual edits; failure retry; edited evidence generates', async ({ page }) => {
  let calls = 0
  await page.route('**/api/lesson-reviews/extract/', async (route) => {
    calls++
    if (calls === 2) return route.fulfill({ status: 502, json: { detail: '识别服务暂时不可用' } })
    await route.fulfill({ json: { text: calls === 1 ? '教学目标：理解三角形' : '教学活动：学生小组讨论', warnings: [] } })
  })
  await page.goto('/lesson-review')
  await page.getByRole('textbox', { name: '材料正文 / 课堂转写' }).fill('老师手动补充')
  await page.locator('input[type=file]').setInputFiles([
    { name: '第一页.docx', mimeType: 'application/octet-stream', buffer: Buffer.from('test') },
    { name: '第二页.png', mimeType: 'image/png', buffer: Buffer.from('test') },
  ])
  await expect(page.getByText('识别服务暂时不可用')).toBeVisible()
  await expect(page.getByRole('textbox', { name: '材料正文 / 课堂转写' })).toHaveValue(/老师手动补充[\s\S]*理解三角形/)
  await page.getByRole('button', { name: '重试识别' }).click()
  await expect(page.getByRole('textbox', { name: '材料正文 / 课堂转写' })).toHaveValue(/学生小组讨论/)
  await page.getByRole('combobox', { name: '分析依据' }).selectOption('lesson_plan')
  await page.route('**/api/lesson-reviews/generate/', (route) => route.fulfill({ json: { id: 42 } }))
  await page.route('**/api/lesson-reviews/42/', (route) => route.fulfill({ json: { id: 42, title: '教案分析', report_content: '教学目标清晰', created_at: new Date().toISOString() } }))
  const request = page.waitForRequest('**/api/lesson-reviews/generate/')
  await page.getByRole('button', { name: '生成分析报告' }).click()
  const posted = (await request).postData()
  expect(posted).toContain('lesson_plan')
  expect(posted).toContain('学生小组讨论')
  await expect(page).toHaveURL(/lesson-reviews\/42$/)
})

test('browser microphone records real blob, stops, transcribes and retains playback', async ({ page }) => {
  await page.route('**/api/asr/transcribe/', async (route) => {
    expect(route.request().postDataBuffer().length).toBeGreaterThan(200)
    await route.fulfill({ json: { text: '请同学们观察三角形。' } })
  })
  await page.goto('/lesson-review')
  await page.getByRole('button', { name: '开始录音' }).click()
  await expect(page.getByRole('timer')).toContainText('录音中')
  await expect(page.getByRole('timer')).toContainText('00:02')
  await page.getByRole('button', { name: '停止并转写' }).click()
  await expect(page.getByRole('textbox', { name: '材料正文 / 课堂转写' })).toHaveValue(/观察三角形/)
  await expect(page.locator('audio')).toBeVisible()
  await expect(page.getByRole('link', { name: '下载这段录音' })).toBeVisible()
})

test('permission denial restores usable controls', async ({ page }) => {
  await page.addInitScript(() => {
    navigator.mediaDevices.getUserMedia = async () => { throw new DOMException('denied', 'NotAllowedError') }
  })
  await page.goto('/lesson-review')
  await page.getByRole('button', { name: '开始录音' }).click()
  await expect(page.getByRole('alert')).toContainText('未获得麦克风权限')
  await expect(page.getByRole('button', { name: '开始录音' })).toBeEnabled()
  await expect(page.getByRole('button', { name: '选择文档、图片或音视频' })).toBeEnabled()
})

test('mobile layout has no horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/lesson-review')
  await expect(page.getByRole('button', { name: '开始录音' })).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)
  expect(overflow).toBe(false)
  await page.screenshot({ path: 'test-results/lesson-review-mobile.png', fullPage: true, animations: 'disabled' })
})
