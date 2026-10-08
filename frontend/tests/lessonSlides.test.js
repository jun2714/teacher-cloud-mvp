import test from 'node:test'
import assert from 'node:assert/strict'
import JSZip from 'jszip'
import { buildLessonSlides, parseLesson, wrapText, SLIDE_WIDTH, SLIDE_HEIGHT, PROGRAM_NAME } from '../src/utils/lessonSlides.js'
import { createLessonPptx } from '../src/utils/lessonPptx.js'

const sample = '# 跟岗研修个人教学设计\n\n**课题名称**：三角形的认识\n**教师姓名**：王老师\n\n## 一、教学目标\n学生能够辨认三角形。\n\n## 二、教学过程设计\n| 环节 | 教师活动 | 学生活动 | 设计意图 | 时间分配 |\n| --- | --- | --- | --- | --- |\n| 导入新课 | 出示图片 | 观察生活中的图形 | 联系生活经验 | 5分钟 |\n| 合作学习 | 引导比较 | 小组讨论 | 形成判断依据 | 10分钟 |\n\n## 三、教学反思\n保留观察记录。'

test('all sections and every teaching process cell appear in slides', () => {
  const slides = buildLessonSlides(sample)
  const text = slides.flatMap((slide) => slide.elements.map((box) => box.text)).join('')
  for (const value of ['三角形的认识', '王老师', '学生能够辨认三角形。', '出示图片', '观察生活中的图形', '联系生活经验', '5分钟', '引导比较', '小组讨论', '形成判断依据', '10分钟', '保留观察记录。']) assert.ok(text.includes(value), value)
  assert.equal(slides.filter((slide) => slide.section === '二、教学过程设计').length, 2)
})

test('long body, metadata, title and table cells paginate without losing text', () => {
  const original = '长段正文用于分页验证。'.repeat(110)
  const title = '非常长的教学课题标题'.repeat(100)
  const slides = buildLessonSlides('## 章节\n' + original, { topic: title })
  const cover = slides.filter((slide) => slide.kind === 'cover')
  const body = slides.filter((slide) => slide.kind === 'content')
  assert.ok(cover.length > 1)
  assert.equal(cover.flatMap((slide) => slide.elements.filter((box) => box.role === 'coverInk').map((box) => box.text)).join(''), title)
  assert.equal(body.flatMap((slide) => slide.elements.filter((box) => box.body).map((box) => box.text)).join(''), original)
  const table = buildLessonSlides('## 过程\n| 环节 | 活动 |\n| --- | --- |\n| 导入 | ' + original + ' |')
  const tableText = table.flatMap((slide) => slide.elements.filter((box) => box.body).map((box) => box.text)).join('')
  assert.ok(tableText.includes(original))
  for (const slide of [...slides, ...table]) {
    for (const box of slide.elements) {
      assert.ok(box.x + box.w <= SLIDE_WIDTH)
      assert.ok(box.y + box.h <= SLIDE_HEIGHT)
    }
  }
})

test('plain text, nested headings, escaped pipes and HTML remain safe text', () => {
  assert.equal(buildLessonSlides('').length, 0)
  assert.ok(buildLessonSlides('没有标题的旧教案').length > 1)
  const parsed = parseLesson('## 教学过程\n### 观察\n| 环节 | 活动 |\n| --- | --- |\n| A | a\\|b<br>继续 |\n<script>alert(1)</script>')
  assert.ok(parsed.sections[0].blocks.some((b) => b.text.includes('a|b\n继续')))
  assert.ok(parsed.sections[0].blocks.some((b) => b.text.includes('<script>')))
  assert.equal(wrapText('long mixed 中文内容', 70, 28).join(''), 'long mixed 中文内容')
})

test('PPTX contains editable text, same page count and selected theme', async () => {
  const slides = buildLessonSlides(sample)
  const deck = await createLessonPptx(slides, { themeId: 'green', title: '三角形' })
  const buffer = await deck.write({ outputType: 'nodebuffer' })
  const zip = await JSZip.loadAsync(buffer)
  const entries = Object.keys(zip.files).filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
  assert.equal(entries.length, slides.length)
  const xml = (await Promise.all(entries.map((name) => zip.file(name).async('string')))).join('')
  assert.ok(xml.includes('173E33'))
  for (const phrase of ['王老师', '出示图片', '保留观察记录。']) assert.ok(xml.includes(phrase), phrase)
  assert.ok(xml.includes('<a:t>'), 'native editable text objects')
  assert.equal(Object.keys(zip.files).filter((name) => name.startsWith('ppt/media/') && !zip.files[name].dir).length, 0)
})

test('personal information stays on the cover and form-only content is omitted from PPTX', async () => {
  const source = '# 跟岗研修个人教学设计\n' + PROGRAM_NAME + '\n> 说明：本表为跟岗期间需完成的个人教学设计成果，将在第六天进行教学成果汇报。\n'
    + '**教师姓名**：张老师\n**所在单位**：实验小学（默认吴忠市吴忠中学）\n**学科**：语文\n**授课年级**：五年级\n**教材版本**：未提供\n**课时安排**：1课时\n**课题名称**：《春》\n**指导教师**：未提供\n**完成日期**：2026-08-31\n'
    + '## 一、教学反思\n本课亮点应保留。\n**指导教师评语**\n这里是评语内容。\n指导教师签字：__________    日期：____年__月__日\n## 二、补充活动\n补充教学内容仍保留。'
  const slides = buildLessonSlides(source)
  const text = (page) => page.elements.map((box) => box.text).join('')
  assert.equal(slides.length, 3)
  for (const field of ['张老师', '实验小学', '语文', '五年级', '1课时', '2026-08-31']) assert.ok(text(slides[0]).includes(field), field)
  const body = slides.slice(1).map(text).join('')
  assert.ok(!body.includes('张老师'))
  assert.ok(body.includes('本课亮点应保留。'))
  assert.ok(body.includes('补充教学内容仍保留。'))
  for (const phrase of ['本表为', '指导教师评语', '这里是评语内容', '指导教师签字', '未提供', '默认']) assert.ok(!slides.map(text).join('').includes(phrase), phrase)
  assert.ok(source.includes('指导教师签字'), 'source text is unchanged')
  const deck = await createLessonPptx(slides)
  const zip = await JSZip.loadAsync(await deck.write({ outputType: 'nodebuffer' }))
  const slideXml = (await Promise.all(Object.keys(zip.files).filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name)).map((name) => zip.file(name).async('string')))).join('')
  assert.ok(!slideXml.includes('指导教师签字'))
  assert.ok(!slideXml.includes('这里是评语内容'))
  assert.ok(slideXml.includes('张老师'))
  const separateReview = buildLessonSlides('## 教学反思\n反思保留\n## 十二、指导教师评语\n评语省略\n签字：___')
  assert.equal(separateReview.length, 2)
})

test('board design retains relative indentation and all six lines on one slide', () => {
  const board = ['                  春', '        盼春 —— 急切、喜悦', '              /    |    \\    \\', '        绘春：春草  春花  春风  春雨  迎春', '             (嫩)  (艳)  (柔)  (细)  (忙)', '        赞春 —— 新、美、力']
  const slides = buildLessonSlides('## 八、板书设计\n```\n' + board.join('\n') + '\n```')
  const pages = slides.filter((slide) => slide.kind === 'content')
  assert.equal(pages.length, 1)
  assert.deepEqual(pages[0].elements.filter((box) => box.body).map((box) => box.text), board.map((row) => row.slice(8)))
})

test('short overflow merges at a readable font size; longer continuations are balanced', () => {
  // Ten compact lines fit; eleven would previously leave one or two lines stranded.
  for (const count of [10, 11, 21]) {
    const lines = Array.from({ length: count }, (_, i) => '教学内容第' + (i + 1) + '行')
    const slides = buildLessonSlides('## 教学设计\n```\n' + lines.join('\n') + '\n```').filter((slide) => slide.kind === 'content')
    const bodies = slides.map((slide) => slide.elements.filter((box) => box.body))
    assert.deepEqual(bodies.flat().map((box) => box.text), lines)
    assert.equal(slides.length, count === 10 ? 1 : count === 11 ? 2 : 3)
    for (const boxes of bodies) {
      assert.ok(boxes.length >= 3)
      assert.ok(boxes.every((box) => box.size >= 26 && box.y + box.h <= 627))
      for (let i = 1; i < boxes.length; i++) assert.ok(boxes[i].y >= boxes[i - 1].y + boxes[i - 1].h - 0.01)
    }
  }
})
