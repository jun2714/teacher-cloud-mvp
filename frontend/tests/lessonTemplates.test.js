import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'
import JSZip from 'jszip'
import { LESSON_TEMPLATES } from '../src/utils/lessonTemplates.js'
import { buildLessonSlides } from '../src/utils/lessonSlides.js'
import { createLessonPptx } from '../src/utils/lessonPptx.js'

const source = '# 个人教学设计\n**教师姓名**：张老师\n**所在单位**：实验小学\n**学科**：语文\n**授课年级**：五年级\n**课时安排**：1课时\n**完成日期**：2026-08-31\n## 教学目标\n通过朗读体会春天的美。\n## 板书设计\n```\n春\n盼春 —— 急切、喜悦\n绘春：春草 春花 春风 春雨 迎春\n赞春 —— 新、美、力\n```\n**指导教师评语**\n指导教师签字：___'

test('four supplied templates retain editable text and embed the exact preview artwork', async () => {
  for (const theme of LESSON_TEMPLATES) {
    const slides = buildLessonSlides(source, { topic: '春', themeId: theme.id })
    assert.equal(slides.length, 3)
    assert.equal(slides[0].backgroundImage, theme.coverImage)
    assert.equal(slides[1].backgroundImage, theme.contentImage)
    for (const slide of slides) {
      for (const box of slide.elements) {
        assert.ok(box.x >= 0 && box.y >= 0 && box.x + box.w <= 1280 && box.y + box.h <= 720)
      }
      if (slide.kind === 'cover') {
        const boxes = slide.elements
        for (let i = 1; i < boxes.length; i++) assert.ok(boxes[i].y >= boxes[i - 1].y + boxes[i - 1].h - 0.01, theme.id + ': cover text overlaps')
      }
    }
    const requested = []
    const originals = []
    const deck = await createLessonPptx(slides, { loadImage: async (url) => {
      requested.push(url)
      const data = await fs.readFile(new URL(url))
      originals.push(data)
      assert.equal(data.readUInt32BE(16), 1280)
      assert.equal(data.readUInt32BE(20), 720)
      return 'data:image/png;base64,' + data.toString('base64')
    } })
    assert.deepEqual(requested, [theme.coverImage, theme.contentImage], 'load only two images per export')
    const zip = await JSZip.loadAsync(await deck.write({ outputType: 'nodebuffer' }))
    const entries = Object.keys(zip.files).filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
    assert.equal(entries.length, slides.length)
    const xml = (await Promise.all(entries.map((name) => zip.file(name).async('string')))).join('')
    for (const text of ['张老师', '通过朗读体会春天的美。', '赞春 —— 新、美、力']) assert.ok(xml.includes(text))
    for (const text of ['YOUR LOGO', 'Created By AI', '指导教师签字']) assert.ok(!xml.includes(text))
    assert.equal((xml.match(/<p:pic>/g) || []).length, slides.length)
    assert.ok(xml.includes('<a:t>'), 'text is native PowerPoint text')
    const images = await Promise.all(Object.keys(zip.files).filter((name) => /^ppt\/media\/.+\.png$/.test(name)).map((name) => zip.file(name).async('nodebuffer')))
    for (const data of originals) assert.ok(images.some((image) => image.equals(data)), 'export artwork matches preview byte for byte')
  }
})

test('narrow template covers wrap long titles without losing text or touching metadata', () => {
  const title = '从多感官描写体会春天的生命力与语言魅力'.repeat(10)
  for (const theme of LESSON_TEMPLATES) {
    const covers = buildLessonSlides(source, { topic: title, themeId: theme.id }).filter((slide) => slide.kind === 'cover')
    const titles = covers.flatMap((slide) => slide.elements.filter((box) => box.role === 'coverInk'))
    assert.equal(titles.map((box) => box.text).join(''), title)
    for (const box of titles) assert.ok(box.y + box.h <= theme.coverLayout.detailsY)
  }
})

test('missing template asset fails the export instead of silently dropping its background', async () => {
  const slides = buildLessonSlides(source, { themeId: 'training-orange' })
  await assert.rejects(createLessonPptx(slides, { loadImage: async () => { throw new Error('asset unavailable') } }), /asset unavailable/)
})
