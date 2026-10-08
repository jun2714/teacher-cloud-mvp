import { SLIDE_THEMES, SLIDE_WIDTH, SLIDE_HEIGHT } from './lessonSlides.js'

async function loadTemplateImage(url) {
  const response = await fetch(url)
  if (!response.ok) throw new Error('模板图片加载失败')
  const bytes = new Uint8Array(await response.arrayBuffer())
  // Chunk conversion avoids a large argument list for full-size template artwork.
  let binary = ''
  for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192))
  return 'data:image/png;base64,' + btoa(binary)
}

export async function createLessonPptx(slides, { themeId = slides[0]?.themeId || 'blue', title = '个人教学设计', loadImage = loadTemplateImage } = {}) {
  if (!slides.length) throw new Error('当前没有可导出的教学设计内容')
  const { default: PptxGenJS } = await import('pptxgenjs')
  const deck = new PptxGenJS()
  const theme = SLIDE_THEMES.find((item) => item.id === themeId) || SLIDE_THEMES.find((item) => item.id === 'blue')
  const images = new Map()
  for (const url of new Set([theme.coverImage, theme.contentImage].filter(Boolean))) images.set(url, await loadImage(url))
  deck.defineLayout({ name: 'LESSON', width: SLIDE_WIDTH / 96, height: SLIDE_HEIGHT / 96 })
  deck.layout = 'LESSON'
  deck.author = '教研云'
  deck.subject = '个人教学设计'
  deck.title = title
  deck.lang = 'zh-CN'
  deck.theme = { headFontFace: 'Microsoft YaHei', bodyFontFace: 'Microsoft YaHei', lang: 'zh-CN' }
  for (const page of slides) {
    const slide = deck.addSlide()
    slide.background = { color: page.kind === 'cover' ? theme.cover : theme.background }
    const artwork = page.kind === 'cover' ? theme.coverImage : theme.contentImage
    if (artwork) slide.addImage({ data: images.get(artwork), x: 0, y: 0, w: SLIDE_WIDTH / 96, h: SLIDE_HEIGHT / 96, altText: theme.name + (page.kind === 'cover' ? '封面背景' : '正文背景') })
    for (const box of page.elements) {
      if (!box.text) continue
      slide.addText(box.text, {
        x: box.x / 96, y: box.y / 96, w: box.w / 96, h: box.h / 96,
        fontFace: 'Microsoft YaHei', fontSize: box.size * 0.75,
        color: theme[box.role], bold: box.bold, margin: 0,
        align: box.align || 'left',
        valign: 'mid', breakLine: false, paraSpaceAfterPt: 0,
      })
    }
    slide.addNotes(page.notes)
  }
  return deck
}

export async function downloadLessonPptx(slides, options) {
  const deck = await createLessonPptx(slides, options)
  const name = (options.title || '个人教学设计').replace(/[\\/:*?"<>|]/g, '_').slice(0, 100)
  await deck.writeFile({ fileName: name + '.pptx' })
}
