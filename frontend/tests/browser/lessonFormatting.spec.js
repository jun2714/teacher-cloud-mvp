import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
import JSZip from 'jszip'

const content = readFileSync(new URL('../fixtures/tengwang.md', import.meta.url), 'utf8')
const plan = { id: 24, title: '个人教学设计 · 滕王阁序', topic: '滕王阁序', generated_content: content, created_at: '2026-10-08T10:00:00Z' }

async function mockPlan(page, source = content) {
  await page.addInitScript(() => localStorage.setItem('access_token', 'test-token'))
  await page.route('**/api/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (!path.startsWith('/api/')) return route.continue()
    return route.fulfill({ json: path === '/api/lesson-plans/24/' ? { ...plan, generated_content: source }
      : path === '/api/me/' ? { id: 1, profile: {} } : {} })
  })
}

test('generated Tengwang slides keep each section on one page across all seven themes', async ({ page }) => {
  await mockPlan(page)
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.addInitScript(() => sessionStorage.setItem('tc_ai_job', JSON.stringify({ kind: 'lesson', title: '滕王阁序', payload: { topic: '滕王阁序' } })))
  await page.route('**/api/lesson-plans/generate-stream/', (route) => route.fulfill({
    contentType: 'text/event-stream', body: 'data: ' + JSON.stringify({ delta: content }) + '\n\ndata: ' + JSON.stringify({ done: true, id: 24, title: plan.title }) + '\n\n',
  }))
  await page.goto('/lesson-plans/output')
  await expect(page.locator('.lesson-slide')).toContainText('滕王阁序')
  for (const name of ['橙黄教育培训模板', '灰色简约教育模板', '紫色教研培训模板', '灰色教师述职模板', '经典蓝样式', '青竹绿样式', '暖杏白样式']) {
    await page.getByRole('button', { name: '使用' + name }).click()
    await page.getByRole('button', { name: '全屏演示', exact: true }).click()
    await expect(page.getByLabel('跳转幻灯片').locator('option')).toHaveCount(3)
    for (const [index, title, end] of [['1', '学情分析', '调整诵读与讲解比例。'], ['2', '板书设计', '穷且益坚']]) {
      await page.getByLabel('跳转幻灯片').selectOption(index)
      await expect(page.locator('.lesson-slide')).toContainText(title)
      await expect(page.locator('.lesson-slide')).toContainText(end)
      const overflow = await page.locator('.slide-text').evaluateAll((boxes) => boxes.filter((box) => box.scrollWidth > box.clientWidth + 2 || box.scrollHeight > box.clientHeight + 2).map((box) => box.textContent))
      expect(overflow, name + title).toEqual([])
      expect(await page.locator('.lesson-slide').innerText()).not.toMatch(/[`*]/)
      if (name === '橙黄教育培训模板') await page.screenshot({ path: `../output/tengwang-${index === '1' ? 'analysis' : 'board'}-fixed.png`, animations: 'disabled' })
    }
    await page.getByRole('button', { name: '退出演示' }).click()
  }
  await page.getByRole('button', { name: '使用橙黄教育培训模板' }).click()
  const downloading = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载 PPT', exact: true }).click()
  const download = await downloading
  expect(await download.failure()).toBeNull()
  const zip = await JSZip.loadAsync(readFileSync(await download.path()))
  const xml = await zip.file('ppt/slides/slide2.xml').async('string')
  expect(xml).toContain('已有知识基础')
  expect(xml).toContain('调整诵读与讲解比例。')
  expect(xml).not.toContain('*注')
  const board = await zip.file('ppt/slides/slide3.xml').async('string')
  expect(board).toContain('滕王阁序')
  expect(board).toContain('穷且益坚')
  expect(board.match(/↓/g)).toHaveLength(2)
})

test('full text renders indented bullets and a complete board without raw fences on mobile', async ({ page }) => {
  await mockPlan(page)
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/lesson-plans/24')
  await page.getByRole('button', { name: '完整正文', exact: true }).click()
  const document = page.locator('.presentation-document')
  await expect(document.locator('ul li')).toHaveCount(3)
  await expect(document.locator('em')).toContainText('注：因未提供具体班级学情数据')
  const board = document.locator('pre code')
  await expect(board).toContainText('滕王阁序\n王勃')
  await expect(board).toContainText('       ↓')
  await expect(board).toContainText('穷且益坚')
  expect(await document.innerText()).not.toContain('```')
  expect(await document.innerText()).not.toContain('- 骈文')
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  await page.screenshot({ path: '../output/tengwang-full-text-fixed.png', fullPage: true, animations: 'disabled' })
})

test('unfinished and longer fences preserve literal symbols and escape HTML', async ({ page }) => {
  const source = '## 板书\n````text\nA * B\n---\n   ↓\n```\n<img src=x onerror="alert(1)">\n````\n\n## 补充\n~~~\n正文尚在生成\n<script>alert(1)</script>'
  await mockPlan(page, source)
  await page.goto('/lesson-plans/24')
  await page.getByRole('button', { name: '完整正文', exact: true }).click()
  const document = page.locator('.presentation-document')
  await expect(document.locator('pre')).toHaveCount(2)
  await expect(document.locator('pre').first()).toContainText('A * B\n---\n   ↓\n```\n<img')
  await expect(document.locator('pre').last()).toContainText('<script>alert(1)</script>')
  await expect(document.locator('img, script')).toHaveCount(0)
})
