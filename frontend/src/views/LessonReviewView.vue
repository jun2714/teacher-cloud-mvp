<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRouter } from 'vue-router'
import { asrApi, lessonApi } from '../api'
import AudioRecorder from '../components/AudioRecorder.vue'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { GRADES, SUBJECTS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'
import { errorMessage, showAlert, showConfirm } from '../utils/dialog'
import { appendMaterial, classifyMaterial, MAX_MATERIAL_CHARS } from '../utils/reviewMaterials'
import { useNoticeStore } from '../stores/notices'

const router = useRouter()
const loading = ref(false)
const processing = ref(false)
const recording = ref(false)
const materials = ref([])
const input = ref(null)
const form = ref({ title: '教学材料与听评课分析', subject: '', grade: '', course_teacher: '', transcript: '', material_kind: 'classroom' })
const busy = computed(() => loading.value || processing.value || recording.value)
let disposed = false
let nextId = 0

onMounted(async () => {
  const profile = await loadTeacherProfile()
  if (disposed) return
  form.value.subject = profile.subject
  form.value.grade = profile.grade
})

async function processMaterial(item) {
  item.status = 'processing'
  item.error = ''
  try {
    const data = item.result || (item.kind === 'media'
      ? await asrApi.transcribe(item.file)
      : await lessonApi.extractReviewMaterial(item.file))
    if (disposed) return
    item.result = data
    const hadContent = Boolean(form.value.transcript.trim())
    form.value.transcript = appendMaterial(form.value.transcript, item.file.name, data.text)
    const nextKind = item.kind === 'media' ? 'classroom' : 'lesson_plan'
    form.value.material_kind = hadContent && form.value.material_kind !== nextKind ? 'mixed' : nextKind
    item.warnings = data.warnings || []
    item.status = 'done'
    item.result = null
  } catch (err) {
    item.status = 'error'
    item.error = errorMessage(err, '识别失败，请重试或粘贴正文')
  }
}

async function addFiles(files) {
  if (busy.value) return
  const selected = Array.from(files || [])
  if (materials.value.length + selected.length > 10) {
    showAlert('一次分析最多添加 10 个文件；多页教案照片请按页序选择。')
    return
  }
  const items = []
  try {
    for (const file of selected) items.push({ id: ++nextId, file, kind: classifyMaterial(file), status: 'queued', warnings: [], error: '' })
  } catch (err) { showAlert(err.message); return }
  materials.value.push(...items)
  processing.value = true
  try {
    for (const item of materials.value.filter((entry) => entry.status === 'queued')) {
      if (disposed) break
      await processMaterial(item)
    }
  } finally { processing.value = false }
}

function chooseFiles(event) {
  const files = Array.from(event.target.files || [])
  event.target.value = ''
  addFiles(files)
}

async function retry(item) {
  if (busy.value) return
  processing.value = true
  try { await processMaterial(item) } finally { processing.value = false }
}

function removeMaterial(item) {
  materials.value = materials.value.filter((entry) => entry.id !== item.id)
}

async function generate() {
  if (busy.value) return
  if (!form.value.transcript.trim()) { showAlert('请先识别材料、录音，或粘贴教学材料正文。'); return }
  if (form.value.transcript.length > MAX_MATERIAL_CHARS) { showAlert('材料超过 60000 字，请拆分分析。'); return }
  if (materials.value.some((item) => item.status === 'error')) {
    showAlert('有材料识别失败，请重试或移除失败文件后再生成，避免遗漏。')
    return
  }
  loading.value = true
  try {
    const payload = new FormData()
    Object.entries(form.value).forEach(([key, value]) => payload.append(key, value))
    const lastMedia = materials.value.filter((item) => item.kind === 'media' && item.status === 'done').at(-1)
    if (lastMedia) payload.append('media_file', lastMedia.file)
    const result = (await lessonApi.generateReview(payload)).data
    useNoticeStore().refresh()
    if (result?.id) router.replace('/lesson-reviews/' + result.id)
  } catch (e) { showAlert(errorMessage(e, '生成失败'), 'error') }
  finally { loading.value = false }
}

function beforeUnload(event) {
  if (recording.value || processing.value) { event.preventDefault(); event.returnValue = '' }
}
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onBeforeRouteLeave(async () => {
  if (recording.value || processing.value) return await showConfirm('正在录音或识别材料，离开将中断当前操作，确定离开吗？')
})
onBeforeUnmount(() => { disposed = true; window.removeEventListener('beforeunload', beforeUnload) })
</script>

<template>
  <main class="sub-page">
    <PageHeader title="听评课助手" back />
    <div class="page-body">
      <section class="feature-intro blue">
        <h2>上传教案或直接录音，解读教学材料</h2>
        <p>支持 Word、PDF、教案照片和课堂音视频。识别后可核对修改，再生成分析报告。</p>
      </section>
      <button type="button" class="history-link" @click="router.push('/lesson-reviews')">查看历史报告 ›</button>
      <section class="form-card" :aria-busy="processing || loading">
        <div class="two-col">
          <label>学科<SuggestInput v-model="form.subject" :options="SUBJECTS" placeholder="可选择或填写" /></label>
          <label>年级<SuggestInput v-model="form.grade" :options="GRADES" placeholder="可选择或填写" /></label>
        </div>
        <label>授课教师<input v-model="form.course_teacher" /></label>
        <AudioRecorder :disabled="processing || loading || materials.length >= 10" @busy="recording = $event" @recorded="addFiles([$event])" />
        <div class="upload-field">
          <b>上传教学材料</b>
          <input ref="input" class="upload-input" type="file" multiple tabindex="-1" aria-label="选择教学材料"
            accept=".docx,.pdf,.jpg,.jpeg,.png,.webp,.mp3,.wav,.m4a,.aac,.amr,.flac,.ogg,.wma,.mp4,.mov,.webm,.avi,.mkv,.mpeg,.mpg"
            :disabled="busy" @change="chooseFiles" />
          <button type="button" class="upload-button" :disabled="busy || materials.length >= 10" @click="input?.click()">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 16V4m-4 4 4-4 4 4M5 16v4h14v-4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
            <span><strong>选择文档、图片或音视频</strong><small>可多选，教案照片请按页序添加</small></span>
          </button>
          <p class="field-hint">最多 10 个文件；Word（.docx）、PDF、图片每个 ≤8MB，音视频每个 ≤80MB。PDF 最多 40 页，其中需图片识别的页面最多 10 页。</p>
          <ul v-if="materials.length" class="material-list" aria-label="已添加材料">
            <li v-for="item in materials" :key="item.id">
              <div class="material-heading"><b>{{ item.file.name }}</b><span role="status">{{ { queued: '等待识别', processing: item.kind === 'media' ? '正在转写…' : '正在识别…', done: '已加入正文', error: '识别失败' }[item.status] }}</span></div>
              <p v-if="item.error" class="material-error" role="alert">{{ item.error }}</p>
              <p v-for="warning in item.warnings" :key="warning" class="field-hint">{{ warning }}</p>
              <div class="material-actions">
                <button v-if="item.status === 'error'" type="button" :disabled="busy" @click="retry(item)">重试识别</button>
                <button type="button" :disabled="busy" @click="removeMaterial(item)">{{ item.status === 'done' ? '移出列表（保留正文）' : '移除' }}</button>
              </div>
            </li>
          </ul>
        </div>
        <label>分析依据
          <select v-model="form.material_kind" :disabled="busy">
            <option value="lesson_plan">教案资料：分析教学设计</option>
            <option value="classroom">课堂实录：分析课堂实施</option>
            <option value="mixed">教案 + 课堂实录：对照分析</option>
          </select>
        </label>
        <p class="field-hint">系统会根据上传材料初选，请按实际内容调整。仅凭教案不判断课堂实际效果。</p>
        <label>材料正文 / 课堂转写<textarea v-model="form.transcript" rows="12" :disabled="loading" placeholder="识别或转写结果会追加到这里，也可直接粘贴教案、听课记录。请核对识别内容后生成。"></textarea></label>
        <p class="field-hint">{{ form.transcript.length }} / 60000 字 · 新材料追加到末尾，保留已输入的内容。</p>
        <button class="primary-button" :disabled="busy" @click="generate">{{ recording ? '请先停止录音' : processing ? '正在识别材料…' : loading ? '正在分析…' : '生成分析报告' }}</button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.history-link { width: 100%; margin: 0 0 12px; padding: 0; border: 0; background: none; color: var(--blue); font-size: 13px; font-weight: 600; text-align: left; min-height: 44px; }
.upload-field { position: relative; }
.upload-input { position: absolute; width: 1px; height: 1px; opacity: 0; pointer-events: none; }
.upload-button { display: flex; align-items: center; gap: 12px; width: 100%; text-align: left; margin-top: 8px; padding: 14px; border: 1px solid #d6e6ff; border-radius: 12px; background: #fff; color: var(--blue); }
.upload-button svg { width: 26px; height: 26px; flex-shrink: 0; }
.upload-button strong, .upload-button small { display: block; line-height: 1.6; }
.upload-button small, .field-hint { color: #53647c; font-size: 12px; font-weight: 400; line-height: 1.7; }
.field-hint { margin: 8px 0 12px; }
.material-list { list-style: none; padding: 0; margin: 12px 0 0; display: grid; gap: 8px; }
.material-list li { border: 1px solid #d6e6ff; border-radius: 10px; padding: 12px; }
.material-heading { display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between; font-size: 13px; }
.material-heading b { overflow-wrap: anywhere; }
.material-heading span { color: #53647c; }
.material-error { font-size: 13px; color: #b42318; line-height: 1.6; }
.material-actions { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 4px; }
.material-actions button { min-height: 44px; padding: 4px 8px; border: 0; background: transparent; color: var(--blue); font-size: 13px; }
button:disabled { opacity: .55; cursor: not-allowed; }
button:focus-visible, a:focus-visible { outline: 2px solid var(--blue); outline-offset: 3px; }
</style>
