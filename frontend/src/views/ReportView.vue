<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { notesApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { GRADES, SUBJECTS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'
import { saveAiJob } from '../utils/aiJob'
import { showAlert } from '../utils/dialog'

const router = useRouter()
const notes = ref([])
const selected = ref([])
const reportType = ref('semester')
const today = new Date().toISOString().slice(0, 10)
const form = ref({
  title: '跟岗研修总结报告',
  teacher_name: '',
  school_name: '吴忠市吴忠中学',
  subject: '',
  grade: '',
  training_period: '',
  training_base: '福建省泉州第一中学',
  advisor: '',
  report_date: today,
})

onMounted(async () => {
  const profile = await loadTeacherProfile()
  form.value.teacher_name = profile.teacher_name
  form.value.school_name = profile.school_name || '吴忠市吴忠中学'
  form.value.subject = profile.subject
  form.value.grade = profile.grade
  notes.value = await notesApi.list()
  selected.value = notes.value.map((n) => n.id)
})

function generate() {
  if (!selected.value.length) {
    showAlert('请至少选择一篇笔记')
    return
  }
  saveAiJob({
    kind: 'report',
    title: form.value.title,
    payload: {
      note_ids: selected.value,
      report_type: reportType.value,
      title: form.value.title,
      teacher_name: form.value.teacher_name,
      school_name: form.value.school_name,
      subject: form.value.subject,
      grade: form.value.grade,
      training_period: form.value.training_period,
      training_base: form.value.training_base,
      advisor: form.value.advisor,
      report_date: form.value.report_date,
    },
  })
  router.push('/reports/output')
}
</script>

<template>
  <main class="sub-page">
    <PageHeader title="研修总结报告" back />
    <div class="page-body">
      <section class="form-card">
        <p class="form-lead">跟岗研修结束后撰写。AI 将按汇报用总结报告格式，依据所选笔记生成。</p>
        <button type="button" class="history-link" @click="router.push('/reports')">查看历史总结 ›</button>
        <label>报告名称<input v-model="form.title" /></label>
        <div class="two-col">
          <label>姓名<input v-model="form.teacher_name" /></label>
          <label>所在单位<input v-model="form.school_name" /></label>
        </div>
        <div class="two-col">
          <label>学科<SuggestInput v-model="form.subject" :options="SUBJECTS" placeholder="可选择或填写" /></label>
          <label>年级<SuggestInput v-model="form.grade" :options="GRADES" placeholder="可选择或填写" /></label>
        </div>
        <label>跟岗时间<input v-model="form.training_period" placeholder="例如：2026年3月1日至2026年3月14日" /></label>
        <div class="two-col">
          <label>跟岗基地<input v-model="form.training_base" /></label>
          <label>指导教师<input v-model="form.advisor" /></label>
        </div>
        <label>报告日期<input v-model="form.report_date" type="date" /></label>
        <h3>选择作为分析依据的笔记</h3>
        <label v-for="note in notes" :key="note.id" class="check-row">
          <input v-model="selected" type="checkbox" :value="note.id" />
          <span><b>{{ note.title }}</b><small>{{ note.category_label }}</small></span>
        </label>
        <button class="primary-button" @click="generate">开始生成</button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.form-lead {
  margin: 0 0 10px;
  font-size: 13px;
  color: #8a93a3;
  line-height: 1.55;
}
.history-link {
  width: 100%;
  margin: 0 0 14px;
  padding: 0;
  border: 0;
  background: none;
  color: var(--blue);
  font-size: 13px;
  font-weight: 600;
  text-align: left;
}
.form-card h3 {
  font-size: 14px;
  margin: 4px 0 10px;
}
</style>
