import { test, expect } from '@playwright/test'
import { buildLessonSlides } from '../../src/utils/lessonSlides.js'

const original = `# 跟岗研修个人教学设计

**教师姓名**：张老师
**所在单位**：吴忠中学
**课题名称**：《春》

> 说明：核对后使用

## 一、教学目标
1. 观察景物。
2. 小组交流。

## 二、教学过程设计
| 环节 | 教师活动 | 学生活动 | 设计意图 | 时间 |
| --- | --- | --- | --- | --- |
| 导入 | 提问<br>交流 | 阅读并讨论 | 联系生活 | 5分钟 |
| 探究 | 分组 | 记录 | 培养合作 | 10分钟 |

## 三、板书设计
\`\`\`text
盼春 —— 急切
  / | \\
绘春 —— 春草 春花
\`\`\`
`

async function setup(page, { fail = false, kind = 'lesson' } = {}) {
  let saved = original
  let saves = 0
  const endpoint = kind === 'lesson' ? 'lesson-plans' : kind === 'review' ? 'lesson-reviews' : 'reports'
  const field = kind === 'lesson' ? 'generated_content' : kind === 'review' ? 'report_content' : 'content'
  const item = () => ({ id: 22, title: '个人教学设计 · 春', topic: '春', [field]: saved, created_at: '2026-10-08T10:00:00Z' })
  await page.addInitScript(() => localStorage.setItem('access_token', 'test-token'))
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (!path.startsWith('/api/')) return route.continue()
    if (path === `/api/${endpoint}/22/save/`) {
      saves++
      if (fail && saves === 1) return route.fulfill({ status: 500, json: { detail: '保存失败，请重试' } })
      saved = route.request().postDataJSON()[field]
      return route.fulfill({ json: item() })
    }
    return route.fulfill({ json: path === `/api/${endpoint}/22/` ? item()
      : path === '/api/me/' ? { id: 1, profile: {} } : { count: 0, results: [] } })
  })
  await page.goto(`/${endpoint}/22`)
  await page.getByRole('button', { name: '编辑内容', exact: true }).click()
  await expect(page.getByRole('textbox', { name: '文档正文' })).toBeVisible()
  return { saved: () => saved, saves: () => saves }
}

test('renders formatted content and an untouched save preserves the exact source', async ({ page }) => {
  const state = await setup(page)
  const editor = page.getByRole('textbox', { name: '文档正文' })
  await expect(editor.locator('h1')).toHaveText('跟岗研修个人教学设计')
  await expect(editor.locator('strong').first()).toHaveText('教师姓名')
  await expect(editor.locator('table tr')).toHaveCount(3)
  await expect(editor.locator('ol li')).toHaveCount(2)
  await expect(editor).not.toContainText('**教师姓名**')
  await page.getByRole('button', { name: '保存修改', exact: true }).click()
  await expect(page.getByRole('button', { name: '编辑内容', exact: true })).toBeVisible()
  expect(state.saved()).toBe(original)
})

test('edits text and table cells, roundtrips Markdown, and updates presentation content', async ({ page }) => {
  const state = await setup(page)
  const editor = page.getByRole('textbox', { name: '文档正文' })
  await editor.locator('td').nth(2).click()
  await page.keyboard.press('End')
  await page.keyboard.insertText('修改后的学生活动')
  await editor.locator('h2').first().click()
  await page.keyboard.press('End')
  await page.keyboard.insertText('（修订）')
  await page.getByRole('button', { name: '保存修改', exact: true }).click()
  await expect(page.getByRole('button', { name: '编辑内容', exact: true })).toBeVisible()
  expect(state.saved()).toContain('## 一、教学目标（修订）')
  expect(state.saved()).toContain('**教师姓名**')
  expect(state.saved()).toContain('盼春 —— 急切')
  expect(state.saved()).toMatch(/提问<br\s*\/?>(?:\s*)交流/)
  expect(JSON.stringify(buildLessonSlides(state.saved(), { topic: '春' }))).toContain('修改后的学生活动')
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await page.getByRole('button', { name: '完整正文', exact: true }).click()
  await expect(page.locator('.presentation-document table')).toContainText('修改后的学生活动')
  await page.getByRole('button', { name: '编辑内容', exact: true }).click()
  await expect(editor.locator('td').nth(2)).toContainText('修改后的学生活动')
  await expect(editor.locator('table tr')).toHaveCount(3)
  await expect(editor.locator('pre')).toContainText('绘春 —— 春草 春花')
})

test('formatting can be undone and a failed save keeps the draft for retry', async ({ page }) => {
  const state = await setup(page, { fail: true })
  const editor = page.getByRole('textbox', { name: '文档正文' })
  await editor.locator('h1').click()
  await page.keyboard.press('End')
  await page.keyboard.insertText('修订标题')
  await page.getByRole('button', { name: '撤销', exact: true }).click()
  await expect(editor.locator('h1')).toHaveText('跟岗研修个人教学设计')
  await page.getByRole('button', { name: '重做', exact: true }).click()
  await expect(editor.locator('h1')).toHaveText('跟岗研修个人教学设计修订标题')
  await page.getByRole('button', { name: '保存修改', exact: true }).click()
  await expect(page.getByText('保存失败，请重试', { exact: true })).toBeVisible()
  await expect(editor.locator('h1')).toHaveText('跟岗研修个人教学设计修订标题')
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await page.getByRole('button', { name: '保存修改', exact: true }).click()
  await expect(page.getByRole('button', { name: '编辑内容', exact: true })).toBeVisible()
  expect(state.saved()).toContain('# 跟岗研修个人教学设计修订标题')
})

for (const kind of ['review', 'report']) {
  test(`${kind} uses the same editor and cancel does not save changes`, async ({ page }) => {
    const state = await setup(page, { kind })
    await page.getByRole('textbox', { name: '文档正文' }).locator('h1').fill('不应保存')
    await page.getByRole('button', { name: '取消', exact: true }).click()
    expect(state.saves()).toBe(0)
    await page.getByRole('button', { name: '编辑内容', exact: true }).click()
    await expect(page.getByRole('textbox', { name: '文档正文' }).locator('h1')).toHaveText('跟岗研修个人教学设计')
  })
}

test('mobile toolbar and wide tables stay within the page', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await setup(page)
  await page.getByRole('textbox', { name: '文档正文' }).locator('td').first().click()
  await expect(page.getByRole('button', { name: '加一行' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.getByRole('button', { name: '加一行' }).click()
  await expect(page.getByRole('textbox', { name: '文档正文' }).locator('tr')).toHaveCount(4)
})
