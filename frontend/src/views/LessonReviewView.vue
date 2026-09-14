<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { asrApi, lessonApi } from '../api'
import FilePicker from '../components/FilePicker.vue'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { GRADES, SUBJECTS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'
import { errorMessage, showAlert } from '../utils/dialog'
import { useNoticeStore } from '../stores/notices'

const router = useRouter()
const loading = ref(false)
const transcribing = ref(false)
const result = ref(null)
const file = ref(null)
const form = ref({ title: '课堂听评课分析', subject: '', grade: '', course_teacher: '', transcript: '' })

onMounted(async () => {
  const profile = await loadTeacherProfile()
  form.value.subject = profile.subject
  form.value.grade = profile.grade
})

async function chooseMedia(picked) {
  file.value = picked || null
  if (!file.value) return
  transcribing.value = true
  try {
    const data = await asrApi.transcribe(file.value)
    if (data?.text) form.value.transcript = data.text
    else showAlert('未识别到有效语音，请换一段录音或手动粘贴转写')
  } catch (err) {
    showAlert(errorMessage(err, '语音转写失败，请粘贴转写后再生成'), 'error')
  } finally {
    transcribing.value = false
  }
}

async function generate() {
  if (!form.value.transcript.trim() && !file.value) {
    showAlert('请粘贴课堂转写，或上传课堂录音/视频由系统转写')
    return
  }
  loading.value = true
  try {
    const fd = new FormData()
    Object.entries(form.value).forEach(([k, v]) => fd.append(k, v))
    if (file.value) fd.append('media_file', file.value)
    result.value = (await lessonApi.generateReview(fd)).data
    useNoticeStore().refresh()
    if (result.value?.id) router.replace(`/lesson-reviews/${result.value.id}`)
  } catch (e) {
    showAlert(errorMessage(e, '生成失败'), 'error')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="sub-page">
    <PageHeader title="听评课助手" back />
    <div class="page-body">
      <section class="feature-intro blue">
        <h2>上传课堂材料，生成听评课分析</h2>
        <p>可上传课堂录音/视频自动转写成文字，也可直接粘贴听课记录，再生成多维评课分析。</p>
      </section>
      <button type="button" class="history-link" @click="router.push('/lesson-reviews')">查看历史报告 ›</button>
      <section class="form-card">
        <div class="two-col">
          <label>学科<SuggestInput v-model="form.subject" :options="SUBJECTS" placeholder="可选择或填写" /></label>
          <label>年级<SuggestInput v-model="form.grade" :options="GRADES" placeholder="可选择或填写" /></label>
        </div>
        <label>授课教师<input v-model="form.course_teacher" /></label>
        <div class="upload-field">
          课堂录音或视频
          <FilePicker
            accept="audio/*,video/*"
            button-text="选择音视频"
            :filename="file?.name"
            :disabled="transcribing || loading"
            :hint="transcribing ? '正在转写，请稍候…' : '支持 mp3 / wav / m4a / mp4 等。转写完成后可在下方修改，再生成报告。'"
            @change="chooseMedia"
            @clear="file = null"
          />
        </div>
        <label>课堂转写文本<textarea v-model="form.transcript" rows="12" placeholder="上传音视频后自动填入，也可直接粘贴听课记录"></textarea></label>
        <button class="primary-button" :disabled="loading || transcribing" @click="generate">
          {{ transcribing ? '正在转写…' : (loading ? '正在分析…' : '生成听评课报告') }}
        </button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.history-link {
  width: 100%;
  margin: 0 0 12px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--blue);
  font-size: 13px;
  font-weight: 600;
  text-align: left;
}
</style>
