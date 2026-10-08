<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import MarkdownBlock from './MarkdownBlock.vue'
import { buildLessonSlides, SLIDE_THEMES, SLIDE_WIDTH, SLIDE_HEIGHT, DEFAULT_LESSON_THEME } from '../utils/lessonSlides'
import { downloadLessonPptx } from '../utils/lessonPptx'

const props = defineProps({ content: { type: String, default: '' }, title: { type: String, default: '个人教学设计' }, topic: { type: String, default: '' } })
const slides = computed(() => buildLessonSlides(props.content, { title: props.title, topic: props.topic, themeId: themeId.value }))
const index = ref(0)
const mode = ref('slides')
function savedTheme() {
  try {
    const id = localStorage.getItem('tc_lesson_ppt_theme')
    if (SLIDE_THEMES.some((item) => item.id === id)) return id
  } catch { /* Storage may be disabled in private browsing. */ }
  return DEFAULT_LESSON_THEME
}
const themeId = ref(savedTheme())
const templates = SLIDE_THEMES.filter((item) => item.coverImage)
const plainThemes = SLIDE_THEMES.filter((item) => !item.coverImage)
const artworkError = ref(false)
const exporting = ref(false)
const error = ref('')
const presenting = ref(false)
const host = ref(null)
const frame = ref(null)
const launchButton = ref(null)
const scale = ref(1)
const current = computed(() => slides.value[index.value])
const theme = computed(() => SLIDE_THEMES.find((item) => item.id === themeId.value) || SLIDE_THEMES[0])
let observer, previousOverflow = '', touchX = null

watch(() => props.content, () => { index.value = Math.min(index.value, Math.max(0, slides.value.length - 1)) })
watch(themeId, (id) => {
  index.value = 0
  artworkError.value = false
  error.value = ''
  try { localStorage.setItem('tc_lesson_ppt_theme', id) } catch { /* Selection still works without storage. */ }
})

function measure() {
  if (!frame.value) return
  const width = frame.value.clientWidth
  const height = presenting.value ? frame.value.clientHeight : width * SLIDE_HEIGHT / SLIDE_WIDTH
  scale.value = Math.max(0.1, Math.min(width / SLIDE_WIDTH, height / SLIDE_HEIGHT))
}

watch([frame, presenting], async () => {
  await nextTick()
  observer?.disconnect()
  if (frame.value) { observer?.observe(frame.value); measure() }
})

async function present() {
  previousOverflow = document.body.style.overflow
  document.body.style.overflow = 'hidden'
  presenting.value = true
  await nextTick()
  host.value?.focus()
  try { await host.value?.requestFullscreen?.() } catch { /* Overlay also works without browser fullscreen. */ }
  measure()
}

async function closePresentation() {
  if (document.fullscreenElement === host.value) {
    try { await document.exitFullscreen() } catch { /* Still close the overlay. */ }
  }
  presenting.value = false
  document.body.style.overflow = previousOverflow
  await nextTick()
  launchButton.value?.focus()
}

function fullScreenChanged() {
  if (presenting.value && !document.fullscreenElement) closePresentation()
}

function move(delta) { index.value = Math.max(0, Math.min(slides.value.length - 1, index.value + delta)) }

function keydown(event) {
  if (presenting.value && event.key === 'Escape') { event.preventDefault(); closePresentation(); return }
  if (presenting.value && event.key === 'Tab') {
    const controls = [...host.value.querySelectorAll('button:not(:disabled), select, [href]')]
    if (!controls.length) return
    if (event.shiftKey && (document.activeElement === controls[0] || document.activeElement === host.value)) {
      event.preventDefault(); controls.at(-1).focus()
    } else if (!event.shiftKey && document.activeElement === controls.at(-1)) {
      event.preventDefault(); controls[0].focus()
    }
    return
  }
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(event.target.tagName)) return
  if (event.target.tagName === 'BUTTON' && event.key === ' ') return
  if (['ArrowRight', 'PageDown', ' '].includes(event.key)) { event.preventDefault(); move(1) }
  if (['ArrowLeft', 'PageUp'].includes(event.key)) { event.preventDefault(); move(-1) }
  if (event.key === 'Home') { event.preventDefault(); index.value = 0 }
  if (event.key === 'End') { event.preventDefault(); index.value = slides.value.length - 1 }
}

function touchEnd(event) {
  if (touchX !== null) {
    const delta = event.changedTouches[0].clientX - touchX
    if (Math.abs(delta) > 50) move(delta < 0 ? 1 : -1)
  }
  touchX = null
}

async function download() {
  if (exporting.value) return
  exporting.value = true
  error.value = ''
  try { await downloadLessonPptx(slides.value, { themeId: themeId.value, title: props.title }) }
  catch { error.value = 'PPT 下载失败，请稍后重试。' }
  finally { exporting.value = false }
}

onMounted(() => {
  observer = new ResizeObserver(measure)
  if (frame.value) observer.observe(frame.value)
  measure()
  document.addEventListener('fullscreenchange', fullScreenChanged)
})
onBeforeUnmount(() => {
  observer?.disconnect()
  document.removeEventListener('fullscreenchange', fullScreenChanged)
  if (presenting.value) {
    document.body.style.overflow = previousOverflow
    if (document.fullscreenElement === host.value) document.exitFullscreen().catch(() => {})
  }
})
</script>

<template>
  <section class="lesson-presentation" aria-label="教学设计演示">
    <div class="presentation-tabs" aria-label="展示方式">
      <button type="button" :aria-pressed="mode === 'slides'" @click="mode = 'slides'">PPT 展示</button>
      <button type="button" :aria-pressed="mode === 'text'" @click="mode = 'text'">完整正文</button>
    </div>
    <div v-if="mode === 'text'" class="presentation-document"><MarkdownBlock :content="content" /></div>
    <template v-else-if="current">
      <div class="presentation-tools">
        <div class="current-theme"><span>演示样式</span><strong aria-live="polite">{{ theme.name }}</strong></div>
        <button type="button" :disabled="exporting || artworkError" @click="download">{{ exporting ? '正在生成 PPT…' : '下载 PPT' }}</button>
      </div>
      <div class="template-options" role="group" aria-label="选择 PPT 模板">
        <button v-for="item in templates" :key="item.id" type="button" class="template-option" :aria-pressed="themeId === item.id" :aria-label="'使用' + item.name + '模板'" :title="item.sourceName" :disabled="exporting" @click="themeId = item.id">
          <img :src="item.coverImage" alt="" loading="lazy" />
          <span>{{ item.name }}</span><small>{{ themeId === item.id ? '已选用' : '点击预览' }}</small>
        </button>
      </div>
      <div class="plain-theme-options" role="group" aria-label="选择简洁样式">
        <button v-for="item in plainThemes" :key="item.id" type="button" :aria-pressed="themeId === item.id" :aria-label="'使用' + item.name + '样式'" :disabled="exporting" @click="themeId = item.id">
          <span class="theme-swatch" :style="{ backgroundColor: '#' + item.cover }" aria-hidden="true"></span>{{ item.name }}<span v-if="themeId === item.id" aria-hidden="true">✓</span>
        </button>
      </div>
      <p v-if="artworkError" class="presentation-error" role="alert">模板背景加载失败，请刷新页面后重试，或选择其他样式。</p>
      <Teleport to="body" :disabled="!presenting">
        <div ref="host" class="presentation-host" :class="{ presenting }" tabindex="0"
          :role="presenting ? 'dialog' : 'region'" :aria-modal="presenting || undefined" aria-label="教学设计幻灯片" @keydown="keydown">
          <header v-if="presenting" class="presentation-top"><span>{{ title }}</span><button type="button" @click="closePresentation">退出演示</button></header>
          <div ref="frame" class="slide-frame" @touchstart.passive="touchX = $event.touches[0].clientX" @touchend.passive="touchEnd">
            <article class="lesson-slide" :data-slide-kind="current.kind" :data-theme="themeId" :aria-label="current.title"
              :style="{ width: SLIDE_WIDTH + 'px', height: SLIDE_HEIGHT + 'px', transform: 'translate(-50%, -50%) scale(' + scale + ')', background: '#' + (current.kind === 'cover' ? theme.cover : theme.background) }">
              <img v-if="current.backgroundImage" :key="current.backgroundImage" class="slide-artwork" :src="current.backgroundImage" alt="" @load="artworkError = false" @error="artworkError = true" />
              <div v-for="(box, boxIndex) in current.elements" :key="boxIndex" class="slide-text"
                :style="{ left: box.x + 'px', top: box.y + 'px', width: box.w + 'px', height: box.h + 'px', fontSize: box.size + 'px', fontWeight: box.bold ? 700 : 400, color: '#' + theme[box.role], justifyContent: box.align === 'center' ? 'center' : 'flex-start', textAlign: box.align || 'left' }">{{ box.text }}</div>
            </article>
          </div>
          <nav class="slide-navigation" aria-label="幻灯片翻页">
            <button type="button" :disabled="index === 0" @click="move(-1)">上一页</button>
            <span role="status" aria-live="polite">{{ index + 1 }} / {{ slides.length }}</span>
            <button type="button" :disabled="index === slides.length - 1" @click="move(1)">下一页</button>
          </nav>
          <label v-if="presenting" class="present-jump">跳转<select v-model.number="index" aria-label="跳转幻灯片"><option v-for="(slide, i) in slides" :key="i" :value="i">{{ i + 1 }}. {{ slide.title }}</option></select></label>
        </div>
      </Teleport>
      <div class="presentation-launch"><button ref="launchButton" type="button" @click="present">全屏演示</button><span>左右滑动或方向键翻页</span></div>
      <label class="slide-jump">章节导航<select v-model.number="index" aria-label="选择幻灯片"><option v-for="(slide, i) in slides" :key="i" :value="i">{{ i + 1 }}. {{ slide.title }}</option></select></label>
      <details class="slide-readable"><summary>阅读本页文字</summary><p v-for="(box, i) in current.elements.filter((box) => box.text)" :key="i">{{ box.text }}</p></details>
      <p class="presentation-hint">个人信息集中展示在封面，PPT 省略填表说明和签字评语。可下载可编辑的 PPT，或切换完整正文查看原文。</p>
    </template>
    <p v-else>暂无可展示内容，请先生成教学设计。</p>
    <p v-if="error" class="presentation-error" role="alert">{{ error }}</p>
  </section>
</template>

<style scoped>
.lesson-presentation { margin-bottom: 16px; }
.presentation-tabs { display: flex; gap: 8px; margin-bottom: 14px; }
.presentation-tabs button { flex: 1; background: #fff; border: 1px solid var(--line); color: var(--text); }
.presentation-tabs button[aria-pressed='true'] { background: #172c4c; color: #fff; border-color: #172c4c; }
button { min-height: 44px; padding: 8px 14px; border: 1px solid #d6dfeb; border-radius: 10px; font-size: 13px; font-weight: 600; background: #fff; color: #172c4c; }
button:disabled { opacity: .4; cursor: not-allowed; }
button:focus-visible, select:focus-visible, summary:focus-visible, .presentation-host:focus-visible { outline: 3px solid #3983e8; outline-offset: 3px; }
.presentation-tools { display: flex; gap: 12px; justify-content: space-between; align-items: end; margin-bottom: 12px; }
.current-theme { display: grid; gap: 5px; font-size: 12px; color: #53647c; min-width: 0; }
.current-theme strong { color: #172c4c; font-size: 14px; overflow-wrap: anywhere; }
.plain-theme-options { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 14px; }
.plain-theme-options button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; flex: 1; padding: 8px; white-space: nowrap; }
.plain-theme-options button[aria-pressed='true'] { border-color: #285ea8; background: #edf4ff; color: #285ea8; }
.theme-swatch { width: 14px; height: 14px; border: 1px solid #c4cdda; border-radius: 50%; flex-shrink: 0; }
.template-options { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-bottom: 14px; }
.template-option { min-width: 0; overflow: hidden; padding: 5px; text-align: left; font-weight: 500; }
.template-option img { display: block; width: 100%; aspect-ratio: 16/9; object-fit: cover; border-radius: 6px; }
.template-option span { display: block; margin: 7px 4px 3px; font-size: 12px; }
.template-option small { display: block; margin: 0 4px 3px; color: #53647c; font-size: 11px; }
.template-option[aria-pressed='true'] { border: 2px solid #285ea8; padding: 4px; background: #edf4ff; }
.template-option[aria-pressed='true'] small { color: #285ea8; font-weight: 600; }
@media (min-width: 768px) { .template-options { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
select { min-height: 44px; border: 1px solid #d6dfeb; border-radius: 10px; padding: 8px; background: #fff; color: #172c4c; font-size: 14px; max-width: 100%; }
.presentation-host { border: 1px solid #d6dfeb; border-radius: 14px; overflow: hidden; background: #fff; }
.slide-frame { position: relative; width: 100%; aspect-ratio: 16/9; overflow: hidden; touch-action: pan-y; }
.lesson-slide { position: absolute; left: 50%; top: 50%; transform-origin: center; font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; }
.slide-artwork { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: fill; pointer-events: none; }
.slide-text { position: absolute; display: flex; align-items: center; white-space: pre; line-height: 1.2; letter-spacing: 0; }
.slide-navigation { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 10px; }
.slide-navigation span { font-size: 13px; font-variant-numeric: tabular-nums; }
.presentation-launch { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin: 12px 0; }
.presentation-launch button { background: #172c4c; color: white; }
.presentation-launch span, .presentation-hint { font-size: 12px; color: #53647c; line-height: 1.7; }
.slide-jump { display: grid; gap: 6px; font-size: 13px; }
.slide-jump select { width: 100%; min-width: 0; }
.slide-readable { padding: 12px; margin-top: 12px; background: #fff; border-radius: 10px; font-size: 14px; line-height: 1.7; overflow-wrap: anywhere; }
.slide-readable summary { cursor: pointer; min-height: 28px; }
.slide-readable p { margin: 8px 0; }
.presentation-document { padding: 16px; background: #fff; border-radius: 14px; border: 1px solid var(--line); }
.presentation-error { color: #b42318; font-size: 13px; }
.presentation-host.presenting { position: fixed; inset: 0; z-index: 5000; border: 0; border-radius: 0; background: #0c1420; color: white; display: flex; flex-direction: column; height: 100dvh; padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left); }
.presenting .slide-frame { flex: 1; aspect-ratio: auto; min-height: 0; }
.presentation-top { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 10px 16px; }
.presentation-top span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
.presenting .slide-navigation { justify-content: center; gap: 28px; padding: 8px 16px; }
.present-jump { display: flex; gap: 10px; align-items: center; justify-content: center; padding: 0 16px 12px; font-size: 13px; }
.present-jump select { max-width: min(75vw, 500px); }
@media (max-height: 500px) { .present-jump { display: none; } .presentation-top { padding: 4px 12px; } .presenting .slide-navigation { padding: 4px 12px; } }
</style>
