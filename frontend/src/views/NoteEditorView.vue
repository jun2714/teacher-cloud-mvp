<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import { asrApi, notesApi } from '../api'
import AudioRecorder from '../components/AudioRecorder.vue'
import FilePicker from '../components/FilePicker.vue'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { GRADES, SUBJECTS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'
import { errorMessage, showAlert, showConfirm } from '../utils/dialog'
import { appendMaterial, classifyMaterial } from '../utils/reviewMaterials'

const router = useRouter()
const route = useRoute()
const noteId = computed(() => route.params.id)
const isEdit = computed(() => Boolean(noteId.value))
const mode = ref('text')
const form = ref({ title: '', content: '', category: 'reflection', subject: '', grade: '', tags: '' })
const sourceFile = ref(null)
const audioFile = ref(null)
const rawText = ref(null)
const savedSourceUrl = ref('')
const savedAudioUrl = ref('')
const saving = ref(false)
const initializing = ref(true)
const extracting = ref(false)
const transcribing = ref(false)
const removing = ref(false)
const recording = ref(false)
const fileError = ref('')
const audioError = ref('')
const fileWarnings = ref([])
const busy = computed(() => initializing.value || saving.value || extracting.value || transcribing.value || removing.value || recording.value)
const modeText = computed(() => ({ text: '手动输入', voice: '语音录入', file: '文件上传' }[mode.value]))
let disposed = false

onMounted(async () => {
  try {
    const profile = await loadTeacherProfile()
    if (disposed) return
    if (isEdit.value) {
      const note = await notesApi.detail(noteId.value)
      if (disposed) return
      form.value = {
        title: note.title || '', content: note.content || '', category: note.category || 'reflection',
        subject: note.subject || profile.subject, grade: note.grade || profile.grade,
        tags: Array.isArray(note.tags) ? note.tags.join('，') : '',
      }
      mode.value = note.input_method || 'text'
      savedSourceUrl.value = note.source_file_url || ''
      savedAudioUrl.value = note.audio_file_url || ''
    } else {
      form.value.subject = profile.subject
      form.value.grade = profile.grade
    }
  } catch (e) {
    showAlert(errorMessage(e, '加载笔记失败，请稍后重试'), 'error')
    if (isEdit.value) router.replace('/notes')
  } finally { initializing.value = false }
})

function clearFile() {
  sourceFile.value = null
  rawText.value = null
  fileError.value = ''
  fileWarnings.value = []
}
function clearAudio() { audioFile.value = null; audioError.value = '' }

async function chooseFile(picked) {
  if (busy.value || !picked) return
  const extension = picked.name.split('.').pop().toLowerCase()
  if (!['pdf', 'docx', 'txt', 'md', 'csv', 'json', 'jpg', 'jpeg', 'png', 'webp'].includes(extension)) {
    showAlert('支持 Word（.docx）、PDF、JPG、PNG、WEBP 或文本文件；旧版 .doc 请另存为 .docx。')
    return
  }
  if (picked.size > 8 * 1024 * 1024) { showAlert('文件不能超过 8MB'); return }
  sourceFile.value = picked
  rawText.value = null
  fileError.value = ''
  fileWarnings.value = []
  extracting.value = true
  try {
    const fd = new FormData()
    fd.append('file', picked)
    const { data } = await notesApi.extract(fd)
    if (disposed) return
    form.value.content = appendMaterial(form.value.content, data.filename || picked.name, data.excerpt)
    rawText.value = data.excerpt
    fileWarnings.value = data.warnings || []
  } catch (err) {
    if (!disposed) fileError.value = errorMessage(err, '文件识别失败，请重试或清除附件后手动填写。')
  } finally { extracting.value = false }
}

async function chooseAudio(picked) {
  if (busy.value || !picked) return
  try {
    if (classifyMaterial(picked) !== 'media') throw new Error('请选择音频文件')
  } catch (err) { showAlert(err.message); return }
  audioFile.value = picked
  audioError.value = ''
  transcribing.value = true
  try {
    const data = await asrApi.transcribe(picked)
    if (disposed) return
    form.value.content = appendMaterial(form.value.content, picked.name, data.text)
  } catch (err) {
    if (!disposed) audioError.value = errorMessage(err, '语音转写失败，请重试或清除附件后手动填写。')
  } finally { transcribing.value = false }
}

function buildFormData() {
  const fd = new FormData()
  Object.entries(form.value).forEach(([k, v]) => {
    fd.append(k, k === 'tags' ? JSON.stringify(String(v).split(/[，,、\s]+/).filter(Boolean)) : v)
  })
  fd.append('input_method', mode.value)
  if (sourceFile.value) {
    fd.append('source_file', sourceFile.value)
    if (rawText.value !== null) fd.append('raw_text', rawText.value)
  }
  if (audioFile.value) fd.append('audio_file', audioFile.value)
  return fd
}

async function submit() {
  if (busy.value) return
  if (fileError.value || audioError.value) {
    showAlert('有附件尚未识别成功，请重试或清除失败附件后再保存。')
    return
  }
  if (!form.value.title.trim() || !form.value.content.trim()) {
    showAlert('请填写标题和笔记内容')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) await notesApi.update(noteId.value, buildFormData())
    else await notesApi.create(buildFormData())
    router.replace('/notes')
  } catch (e) {
    const details = e?.response?.data
    const fieldError = details && Object.values(details).find((value) => Array.isArray(value))
    showAlert(fieldError ? fieldError.join('；') : errorMessage(e, '保存失败'), 'error')
  } finally { saving.value = false }
}

async function removeNote() {
  if (!isEdit.value || busy.value) return
  const ok = await showConfirm('删除笔记「' + (form.value.title || '未命名') + '」？删除后不可恢复。')
  if (!ok || busy.value) return
  removing.value = true
  try {
    await notesApi.remove(noteId.value)
    router.replace('/notes')
  } catch (e) { showAlert(errorMessage(e, '删除失败'), 'error') }
  finally { removing.value = false }
}

function beforeUnload(event) {
  if (recording.value || extracting.value || transcribing.value) { event.preventDefault(); event.returnValue = '' }
}
onMounted(() => window.addEventListener('beforeunload', beforeUnload))
onBeforeRouteLeave(async () => {
  if (recording.value || extracting.value || transcribing.value) {
    return await showConfirm('正在录音或识别材料，离开将中断当前操作，确定离开吗？')
  }
})
onBeforeUnmount(() => { disposed = true; window.removeEventListener('beforeunload', beforeUnload) })
</script>

<template>
  <main class="sub-page">
    <PageHeader :title="isEdit ? '编辑教研笔记' : '新增教研笔记'" back />
    <div class="page-body">
      <div class="mode-tabs">
        <button v-for="item in ['text','voice','file']" :key="item" type="button" :disabled="busy" :class="{ active: mode === item }" @click="mode = item">
          {{ { text: '手动输入', voice: '语音录入', file: '文件上传' }[item] }}
        </button>
      </div>
      <p v-if="initializing" role="status">正在加载笔记…</p>
      <section v-else class="form-card" :aria-busy="saving || extracting || transcribing">
        <fieldset :disabled="saving || removing" class="note-fields">
        <label>笔记标题<input v-model="form.title" maxlength="200" placeholder="例如：今天课堂中的一个新发现" /></label>
        <div class="two-col">
          <label>类型
            <select v-model="form.category">
              <option value="reflection">教学反思</option>
              <option value="learning">学习心得</option>
              <option value="lesson_review">听评课</option>
              <option value="collective">集体备课</option>
              <option value="idea">教学灵感</option>
            </select>
          </label>
          <label>学科<SuggestInput v-model="form.subject" :options="SUBJECTS" placeholder="可选择或填写" /></label>
        </div>
        <label>年级<SuggestInput v-model="form.grade" :options="GRADES" placeholder="可选择或填写" /></label>
        <div v-if="mode === 'voice'" class="voice-panel">
          <p>可直接录音，停止后自动转写；也可上传课堂/会议录音。结果追加到正文，可继续修改。</p>
          <AudioRecorder :disabled="saving || extracting || transcribing || removing" @busy="recording = $event" @recorded="chooseAudio" />
          <FilePicker
            accept="audio/*"
            button-text="上传音频转写"
            :filename="audioFile?.name"
            :disabled="busy"
            :hint="transcribing ? '正在转写音频，请稍候…' : '支持 mp3 / wav / m4a / webm 等录音，每个不超过 80MB。'"
            @change="chooseAudio"
            @clear="clearAudio"
          />
          <div v-if="audioError" class="import-error" role="alert">
            <p>{{ audioError }}</p>
            <button type="button" class="secondary-button" :disabled="busy" @click="chooseAudio(audioFile)">重试转写</button>
          </div>
          <p v-else-if="audioFile && !transcribing" class="import-hint" role="status">转写已加入正文，保存前请核对。</p>
          <audio v-if="savedAudioUrl" :src="savedAudioUrl" controls aria-label="已保存的录音" />
        </div>
        <div v-if="mode === 'file'" class="upload-panel">
          <FilePicker
            accept=".pdf,.docx,.txt,.md,.csv,.json,.jpg,.jpeg,.png,.webp"
            button-text="选择文档或图片"
            :filename="sourceFile?.name"
            :disabled="busy"
            :hint="extracting ? '正在识别正文，请稍候…' : '支持 Word（.docx）、PDF、教案图片及文本文件，每个不超过 8MB；PDF 最多 40 页，其中需图片识别的页面最多 10 页。'"
            @change="chooseFile"
            @clear="clearFile"
          />
          <div v-if="fileError" class="import-error" role="alert">
            <p>{{ fileError }}</p>
            <button type="button" class="secondary-button" :disabled="busy" @click="chooseFile(sourceFile)">重试识别</button>
          </div>
          <p v-for="warning in fileWarnings" :key="warning" class="import-hint">{{ warning }}</p>
          <p v-if="sourceFile && !extracting && !fileError" class="import-hint" role="status">识别已加入正文，保存时以您修改后的内容为准。</p>
          <a v-if="savedSourceUrl" :href="savedSourceUrl" target="_blank" rel="noopener">查看已保存的原文件</a>
        </div>
        <p v-if="sourceFile || audioFile" class="import-hint">再次导入会追加正文；清除附件不会删除已导入文字。每类附件保留最后选择的一份。</p>
        <label>笔记内容
          <textarea v-model="form.content" rows="12" :placeholder="`${modeText}后的内容可以在这里检查和修改`"></textarea>
        </label>
        <label>标签<input v-model="form.tags" placeholder="新课标, 教学设计, 课堂参与" /></label>
        </fieldset>
        <button class="primary-button" type="button" :disabled="busy" @click="submit">
          {{ recording ? '请先停止录音' : extracting ? '正在识别…' : transcribing ? '正在转写…' : saving ? '保存中…' : isEdit ? '保存修改' : '保存笔记' }}
        </button>
        <button v-if="isEdit" class="danger-button" type="button" :disabled="busy" @click="removeNote">
          {{ removing ? '删除中…' : '删除笔记' }}
        </button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.note-fields { border: 0; padding: 0; margin: 0; min-width: 0; }
.import-hint { font-size: 13px; line-height: 1.6; color: #53647c; }
.import-error { color: #b42318; font-size: 13px; line-height: 1.6; }
.voice-panel audio { width: 100%; margin-top: 12px; }
button:disabled { opacity: .55; cursor: not-allowed; }
.danger-button {
  width: 100%;
  margin-top: 10px;
  min-height: 44px;
  border: 0;
  border-radius: 12px;
  background: #fff1f0;
  color: #f04438;
  font-weight: 700;
}
</style>
