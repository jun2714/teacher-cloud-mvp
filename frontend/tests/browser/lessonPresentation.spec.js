import { test, expect } from '@playwright/test'

const content = '# 跟岗研修个人教学设计\n\n吴忠中学教师跟岗实践暨“县中帮扶”交流培训\n\n**课题名称**：三角形的认识\n**教师姓名**：王老师\n**授课年级**：高一\n\n## 一、教材分析\n本课以生活中的三角形为切入点，引导学生通过观察、操作与比较认识图形特征。\n\n## 二、教学目标\n1. 认识三角形的基本特征。\n2. 通过合作探究建立分类依据。\n\n## 三、教学过程设计\n| 环节 | 教师活动 | 学生活动 | 设计意图 | 时间分配 |\n| --- | --- | --- | --- | --- |\n| 导入新课 | 出示生活中的图形图片，提出观察任务 | 观察并描述图形的共同点 | 联系生活经验，激活已有认知 | 5分钟 |\n| 合作学习 | 提供不同三角形，组织比较与讨论 | 分组观察边与角，并记录结论 | 建立分类标准，形成判断依据 | 10分钟 |\n\n## 四、教学反思\n' + '通过学生的观察记录判断目标达成情况，后续继续关注表达与论证过程。'.repeat(15)
const plan = { id: 22, title: '个人教学设计 · 三角形的认识', topic: '三角形的认识', generated_content: content, created_at: '2026-10-08T10:00:00Z' }

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('access_token', 'test-token'))
  await page.route('**/api/**', async (route) => {
    const path = new URL(route.request().url()).pathname
    if (!path.startsWith('/api/')) return route.continue()
    const json = path === '/api/lesson-plans/22/' ? plan
      : path === '/api/me/' ? { id: 1, profile: {} }
        : path.includes('notices') ? { count: 0, results: [] } : {}
    await route.fulfill({ json })
  })
})

test('history opens as slides, supports themes and full text, and downloads editable PPT', async ({ page }) => {
  await page.goto('/lesson-plans/22')
  await expect(page.getByRole('button', { name: 'PPT 展示', exact: true })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('.lesson-slide')).toContainText('三角形的认识')
  await expect(page.locator('.lesson-slide')).toContainText('王老师')
  await page.getByRole('button', { name: '使用青竹绿样式' }).click()
  await expect(page.locator('.lesson-slide')).toHaveCSS('background-color', 'rgb(23, 62, 51)')
  await page.getByRole('button', { name: '下一页' }).click()
  await expect(page.locator('.lesson-slide')).toContainText('一、教材分析')
  const download = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载 PPT', exact: true }).click()
  const file = await download
  expect(file.suggestedFilename()).toMatch(/\.pptx$/)
  expect(await file.failure()).toBeNull()
  await file.saveAs('test-results/lesson-presentation.pptx')
  await page.getByRole('button', { name: '完整正文', exact: true }).click()
  await expect(page.locator('.presentation-document')).toContainText('教学反思')
  await expect(page.locator('.presentation-document table')).toBeVisible()
})

test('all pages fit, full screen works with keyboard and restores focus', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.goto('/lesson-plans/22')
  await page.getByRole('button', { name: '全屏演示', exact: true }).click()
  await expect(page.getByRole('dialog', { name: '教学设计幻灯片' })).toBeVisible()
  await page.screenshot({ path: 'test-results/lesson-presentation-cover.png', animations: 'disabled' })
  const options = await page.getByLabel('跳转幻灯片').locator('option').count()
  for (let i = 0; i < options; i++) {
    await page.getByLabel('跳转幻灯片').selectOption(String(i))
    const overflow = await page.locator('.slide-text').evaluateAll((boxes) => boxes.filter((box) => box.scrollWidth > box.clientWidth + 2 || box.scrollHeight > box.clientHeight + 2).map((box) => box.textContent))
    expect(overflow).toEqual([])
  }
  const processIndex = await page.getByLabel('跳转幻灯片').locator('option').evaluateAll((options) => options.findIndex((o) => o.textContent.includes('教学过程设计')))
  await page.getByLabel('跳转幻灯片').selectOption(String(processIndex))
  await page.screenshot({ path: 'test-results/lesson-presentation-process.png', animations: 'disabled' })
  await page.locator('.presentation-host').focus()
  await page.keyboard.press('Home')
  await expect(page.locator('.lesson-slide')).toHaveAttribute('data-slide-kind', 'cover')
  await page.keyboard.press('ArrowRight')
  await expect(page.locator('.lesson-slide')).toHaveAttribute('data-slide-kind', 'content')
  await page.getByRole('button', { name: '退出演示' }).click()
  await expect(page.getByRole('button', { name: '全屏演示', exact: true })).toBeFocused()
  expect(await page.evaluate(() => document.body.style.overflow)).not.toBe('hidden')
})

test('completed generation automatically displays slides; saved edits regenerate slides', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('tc_ai_job', JSON.stringify({ kind: 'lesson', title: '三角形的认识', payload: { topic: '三角形的认识' } })))
  await page.route('**/api/lesson-plans/generate-stream/', (route) => route.fulfill({
    contentType: 'text/event-stream', body: 'data: ' + JSON.stringify({ delta: content }) + '\n\ndata: ' + JSON.stringify({ done: true, id: 22, title: plan.title }) + '\n\n',
  }))
  await page.goto('/lesson-plans/output')
  await expect(page.locator('.lesson-slide')).toContainText('三角形的认识')
  await expect(page.locator('.lesson-slide')).toContainText('王老师')
  await page.getByRole('button', { name: '查看并编辑' }).click()
  await page.getByRole('button', { name: '编辑内容', exact: true }).click()
  await page.getByRole('textbox', { name: '文档正文' }).click()
  await page.keyboard.press('ControlOrMeta+A')
  await page.keyboard.insertText('个人教学设计')
  await page.getByLabel('段落样式').selectOption('1')
  await page.keyboard.press('End')
  await page.keyboard.press('Enter')
  await page.keyboard.insertText('新教学目标')
  await page.getByLabel('段落样式').selectOption('2')
  await page.keyboard.press('End')
  await page.keyboard.press('Enter')
  await page.keyboard.insertText('编辑后新增的关键目标')
  await page.route('**/api/lesson-plans/22/save/', (route) => {
    const updated = route.request().postDataJSON().generated_content
    expect(updated).toContain('## 新教学目标')
    return route.fulfill({ json: { ...plan, generated_content: updated } })
  })
  await page.getByRole('button', { name: '保存修改', exact: true }).click()
  await page.getByRole('button', { name: '确定', exact: true }).click()
  await page.getByRole('button', { name: '下一页' }).click()
  await expect(page.locator('.lesson-slide')).toContainText('编辑后新增的关键目标')
})

test('mobile and landscape presentation fit without horizontal overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/lesson-plans/22')
  await expect(page.locator('.lesson-slide')).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  await page.screenshot({ path: 'test-results/lesson-presentation-mobile.png', fullPage: true, animations: 'disabled' })
  await page.getByRole('button', { name: '全屏演示', exact: true }).click()
  await page.setViewportSize({ width: 844, height: 390 })
  await page.getByRole('button', { name: '下一页' }).click()
  await expect(page.locator('.lesson-slide')).toContainText('一、教材分析')
  await page.screenshot({ path: 'test-results/lesson-presentation-landscape.png', animations: 'disabled' })
  await page.getByRole('button', { name: '退出演示' }).click()
})

test('interrupted generation does not present incomplete content as saved slides', async ({ page }) => {
  await page.addInitScript(() => sessionStorage.setItem('tc_ai_job', JSON.stringify({ kind: 'lesson', title: '三角形', payload: { topic: '三角形' } })))
  await page.route('**/api/lesson-plans/generate-stream/', (route) => route.fulfill({
    contentType: 'text/event-stream', body: 'data: ' + JSON.stringify({ delta: '# 尚未完成的教案' }) + '\n\n',
  }))
  await page.goto('/lesson-plans/output')
  await expect(page.getByText('连接已中断，尚未确认保存完成。请先查看历史记录，或返回重试。')).toBeVisible()
  await expect(page.locator('.lesson-slide')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '查看并编辑' })).toBeDisabled()
})

test('all four supplied templates preview without overflow and download with the selected artwork', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 960 })
  await page.goto('/lesson-plans/22')
  await expect(page.getByRole('button', { name: '使用橙黄教育培训模板' })).toHaveAttribute('aria-pressed', 'true')
  for (const [id, name] of [['training-orange', '橙黄教育培训'], ['education-grey', '灰色简约教育'], ['research-purple', '紫色教研培训'], ['teacher-grey', '灰色教师述职']]) {
    await page.getByRole('button', { name: '使用' + name + '模板' }).click()
    await expect(page.locator('.lesson-slide')).toHaveAttribute('data-theme', id)
    await expect(page.locator('.lesson-slide')).toContainText('王老师')
    await expect(page.locator('.slide-artwork')).toHaveJSProperty('complete', true)
    expect(await page.locator('.slide-artwork').evaluate((image) => image.naturalWidth)).toBe(1280)
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: '下载 PPT', exact: true }).click()
    const file = await download
    expect(await file.failure()).toBeNull()
    await file.saveAs('test-results/template-' + id + '.pptx')
    await page.getByRole('button', { name: '全屏演示', exact: true }).click()
    await page.screenshot({ path: 'test-results/template-' + id + '-cover.png', animations: 'disabled' })
    const count = await page.getByLabel('跳转幻灯片').locator('option').count()
    for (let i = 0; i < count; i++) {
      await page.getByLabel('跳转幻灯片').selectOption(String(i))
      const overflow = await page.locator('.slide-text').evaluateAll((boxes) => boxes.filter((box) => box.scrollWidth > box.clientWidth + 2 || box.scrollHeight > box.clientHeight + 2).map((box) => box.textContent))
      expect(overflow, id + ' page ' + i).toEqual([])
    }
    await page.getByLabel('跳转幻灯片').selectOption('1')
    await page.screenshot({ path: 'test-results/template-' + id + '-content.png', animations: 'disabled' })
    await page.getByRole('button', { name: '退出演示' }).click()
  }
  await page.reload()
  await expect(page.getByRole('button', { name: '使用灰色教师述职模板' })).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('.lesson-slide')).toHaveAttribute('data-slide-kind', 'cover')
})

test('template thumbnails support mobile selection and return to cover', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/lesson-plans/22')
  await page.getByRole('button', { name: '下一页' }).click()
  const option = page.getByRole('button', { name: '使用紫色教研培训模板' })
  await option.click()
  await expect(option).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('.lesson-slide')).toHaveAttribute('data-slide-kind', 'cover')
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  await page.screenshot({ path: 'test-results/template-mobile-picker.png', fullPage: true, animations: 'disabled' })
})

test('inline style choices remain inside the page and work with keyboard without native popup', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/lesson-plans/22')
  await expect(page.locator('.presentation-tools select')).toHaveCount(0)
  for (const [id, name] of [['blue', '经典蓝'], ['green', '青竹绿'], ['paper', '暖杏白']]) {
    const button = page.getByRole('button', { name: '使用' + name + '样式' })
    await button.focus()
    await page.keyboard.press('Enter')
    await expect(button).toHaveAttribute('aria-pressed', 'true')
    await expect(button).toBeFocused()
    await expect(page.locator('.lesson-slide')).toHaveAttribute('data-theme', id)
    await expect(page.locator('.lesson-slide')).toContainText('王老师')
    await expect(page.locator('.current-theme')).toContainText(name)
    expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)).toBe(false)
  }
  await page.getByRole('button', { name: '使用紫色教研培训模板' }).click()
  await expect(page.locator('.lesson-slide')).toHaveAttribute('data-theme', 'research-purple')
  await expect(page.getByRole('group', { name: '选择简洁样式' }).locator('[aria-pressed="true"]')).toHaveCount(0)
  await page.screenshot({ path: 'test-results/inline-style-picker.png', fullPage: true, animations: 'disabled' })
})
