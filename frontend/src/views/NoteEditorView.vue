<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { asrApi, notesApi } from '../api'
import FilePicker from '../components/FilePicker.vue'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { GRADES, SUBJECTS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'
import { errorMessage, showAlert, showConfirm } from '../utils/dialog'

const router = useRouter()
const route = useRoute()
const noteId = computed(() => route.params.id)
const isEdit = computed(() => Boolean(noteId.value))
const mode = ref('text')
const form = ref({ title: '', content: '', category: 'reflection', subject: '', grade: '', tags: '' })
const sourceFile = ref(null)
const audioFile = ref(null)
const saving = ref(false)
const extracting = ref(false)
const transcribing = ref(false)
const removing = ref(false)
const recording = ref(false)
let recognition = null

onMounted(async () => {
  const profile = await loadTeacherProfile()
  if (isEdit.value) {
    try {
      const note = await notesApi.detail(noteId.value)
      form.value = {
        title: note.title || '',
        content: note.content || '',
        category: note.category || 'reflection',
        subject: note.subject || profile.subject,
        grade: note.grade || profile.grade,
        tags: Array.isArray(note.tags) ? note.tags.join('，') : '',
      }
      mode.value = note.input_method || 'text'
    } catch (e) {
      showAlert(errorMessage(e, '笔记不存在或已删除'), 'error')
      router.replace('/notes')
    }
    return
  }
  form.value.subject = profile.subject
  form.value.grade = profile.grade
})

const modeText = computed(() => ({ text: '手动输入', voice: '语音录入', file: '文件上传' }[mode.value]))

async function chooseFile(picked) {
  const file = picked || null
  sourceFile.value = file
  if (!file) return
  extracting.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const { data } = await notesApi.extract(fd)
    if (data?.excerpt) {
      const block = `【来自文件：${data.filename}】\n${data.excerpt}`
      form.value.content = form.value.content.trim()
        ? `${form.value.content.trim()}\n\n${block}`
        : data.excerpt
    }
  } catch (err) {
    showAlert(errorMessage(err, '文件解析失败，仍可保存原文件'), 'error')
  } finally {
    extracting.value = false
  }
}

function startVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!SpeechRecognition) {
    showAlert('当前浏览器不支持直接语音录入，请改用下方「上传音频」自动转写，或换 Chrome/Edge。')
    return
  }
  recognition = new SpeechRecognition()
  recognition.lang = 'zh-CN'
  recognition.continuous = true
  recognition.interimResults = true
  recognition.onresult = (event) => {
    let text = ''
    for (let i = event.resultIndex; i < event.results.length; i++) text += event.results[i][0].transcript
    form.value.content += text
  }
  recognition.onend = () => { recording.value = false }
  recognition.start()
  recording.value = true
}
function stopVoice() { recognition?.stop(); recording.value = false }

async function chooseAudio(picked) {
  audioFile.value = picked || null
  if (!audioFile.value) return
  transcribing.value = true
  try {
    const data = await asrApi.transcribe(audioFile.value)
    if (data?.text) {
      form.value.content = form.value.content.trim()
        ? `${form.value.content.trim()}\n\n${data.text}`
        : data.text
    } else {
      showAlert('未识别到有效语音，请换一段录音或手动填写正文')
    }
  } catch (err) {
    showAlert(errorMessage(err, '语音转写失败，请手动填写正文'), 'error')
  } finally {
    transcribing.value = false
  }
}

function buildFormData() {
  const fd = new FormData()
  Object.entries(form.value).forEach(([k, v]) => {
    fd.append(k, k === 'tags' ? JSON.stringify(String(v).split(/[，,、\s]+/).filter(Boolean)) : v)
  })
  fd.append('input_method', mode.value)
  if (sourceFile.value) fd.append('source_file', sourceFile.value)
  if (audioFile.value) fd.append('audio_file', audioFile.value)
  return fd
}

async function submit() {
  if (!form.value.title.trim() || !form.value.content.trim()) {
    showAlert('请填写标题和笔记内容')
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await notesApi.update(noteId.value, buildFormData())
    } else {
      await notesApi.create(buildFormData())
    }
    router.replace('/notes')
  } catch (e) {
    showAlert(errorMessage(e, '保存失败'), 'error')
  } finally {
    saving.value = false
  }
}

async function removeNote() {
  if (!isEdit.value) return
  const ok = await showConfirm(`删除笔记「${form.value.title || '未命名'}」？删除后不可恢复。`)
  if (!ok) return
  removing.value = true
  try {
    await notesApi.remove(noteId.value)
    router.replace('/notes')
  } catch (e) {
    showAlert(errorMessage(e, '删除失败'), 'error')
  } finally {
    removing.value = false
  }
}
</script>

<template>
  <main class="sub-page">
    <PageHeader :title="isEdit ? '编辑教研笔记' : '新增教研笔记'" back />
    <div class="page-body">
      <div class="mode-tabs">
        <button v-for="item in ['text','voice','file']" :key="item" type="button" :class="{ active: mode === item }" @click="mode = item">
          {{ { text: '手动输入', voice: '语音录入', file: '文件上传' }[item] }}
        </button>
      </div>
      <section class="form-card">
        <label>笔记标题<input v-model="form.title" placeholder="例如：今天课堂中的一个新发现" /></label>
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
          <p>可现场语音转文字，或上传课堂/会议录音由系统转写。转写结果仍可继续修改。</p>
          <button class="secondary-button" type="button" @click="recording ? stopVoice() : startVoice()">
            {{ recording ? '停止录音' : '开始语音录入' }}
          </button>
          <FilePicker
            accept="audio/*"
            button-text="上传音频转写"
            :filename="audioFile?.name"
            :disabled="transcribing || saving"
            :hint="transcribing ? '正在转写音频，请稍候…' : '支持 mp3 / wav / m4a 等课堂或会议录音。'"
            @change="chooseAudio"
            @clear="audioFile = null"
          />
        </div>
        <div v-if="mode === 'file'" class="upload-panel">
          <FilePicker
            accept=".pdf,.docx,.txt,.md,.csv,.json,image/*"
            button-text="选择文档"
            :filename="sourceFile?.name"
            :disabled="extracting || saving"
            :hint="extracting ? '正在抽取正文…' : '支持 txt / md / docx / pdf。抽取的文字会填入下方正文，可再修改。'"
            @change="chooseFile"
            @clear="sourceFile = null"
          />
        </div>
        <label>笔记内容
          <textarea v-model="form.content" rows="12" :placeholder="`${modeText}后的内容可以在这里检查和修改`"></textarea>
        </label>
        <label>标签<input v-model="form.tags" placeholder="新课标, 教学设计, 课堂参与" /></label>
        <button class="primary-button" type="button" :disabled="saving || extracting || transcribing" @click="submit">
          {{ transcribing ? '正在转写…' : (saving ? '保存中…' : (isEdit ? '保存修改' : '保存笔记')) }}
        </button>
        <button v-if="isEdit" class="danger-button" type="button" :disabled="removing" @click="removeNote">
          {{ removing ? '删除中…' : '删除笔记' }}
        </button>
      </section>
    </div>
  </main>
</template>

<style scoped>
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
