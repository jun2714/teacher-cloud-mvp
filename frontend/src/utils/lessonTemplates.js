// Artwork extracted from the user's PPTX files; see assets/lesson-templates/README.md.
export const DEFAULT_LESSON_THEME = 'training-orange'
export const LESSON_TEMPLATES = [
  {
    id: 'training-orange', name: '橙黄教育培训', sourceName: '橙黄扁平简约教育培训模版.pptx',
    background: 'FCF5E5', ink: '42372E', accent: 'B55024', muted: '716353', cover: 'FFFFFF', coverInk: 'C55425', coverMuted: '675446',
    coverImage: new URL('../assets/lesson-templates/training-orange-cover.png', import.meta.url).href,
    contentImage: new URL('../assets/lesson-templates/training-orange-content.png', import.meta.url).href,
    coverLayout: { x: 240, width: 800, programY: 154, labelY: 204, titleY: 266, titleHeight: 140, detailsY: 436, detailsSize: 22, align: 'center' },
  },
  {
    id: 'education-grey', name: '灰色简约教育', sourceName: '灰色简约教育通用.pptx',
    background: 'E4EAF8', ink: '263C52', accent: '1979BB', muted: '526579', cover: 'E4EAF8', coverInk: '1879BC', coverMuted: '3E566C',
    coverImage: new URL('../assets/lesson-templates/education-grey-cover.png', import.meta.url).href,
    contentImage: new URL('../assets/lesson-templates/education-grey-content.png', import.meta.url).href,
    coverLayout: { x: 70, width: 710, programY: 70, labelY: 173, titleY: 241, titleHeight: 195, detailsY: 478, detailsSize: 23 },
  },
  {
    id: 'research-purple', name: '紫色教研培训', sourceName: '紫色教研培训报演示模板.pptx',
    background: 'FFFFFF', ink: '383047', accent: '7950A5', muted: '6D607A', cover: 'DED5F6', coverInk: '493363', coverMuted: '55446A',
    coverImage: new URL('../assets/lesson-templates/research-purple-cover.png', import.meta.url).href,
    contentImage: new URL('../assets/lesson-templates/research-purple-content.png', import.meta.url).href,
    coverLayout: { x: 52, width: 660, programY: 46, labelY: 192, titleY: 258, titleHeight: 145, detailsY: 433, detailsSize: 22 },
  },
  {
    id: 'teacher-grey', name: '灰色教师述职', sourceName: '灰色简约教师述职演示模板.pptx',
    background: 'BDBDBD', ink: '242424', accent: '303030', muted: '424242', cover: '4E514D', coverInk: 'FFFFFF', coverMuted: 'F1E8DC',
    coverImage: new URL('../assets/lesson-templates/teacher-grey-cover.png', import.meta.url).href,
    contentImage: new URL('../assets/lesson-templates/teacher-grey-content.png', import.meta.url).href,
    coverLayout: { x: 70, width: 610, programY: 76, labelY: 182, titleY: 246, titleHeight: 185, detailsY: 478, detailsSize: 22 },
  },
]
