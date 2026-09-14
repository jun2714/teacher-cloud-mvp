<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { GRADES, SUBJECTS, TEXTBOOKS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'
import { saveAiJob } from '../utils/aiJob'
import { showAlert } from '../utils/dialog'

const router = useRouter()
const today = new Date().toISOString().slice(0, 10)
const form = ref({
  teacher_name: '',
  school_name: '',
  subject: '',
  grade: '',
  textbook: '',
  class_hours: 1,
  topic: '',
  advisor: '',
  complete_date: today,
  student_context: '',
  requirements: '对齐新课标，突出核心素养与学生实践',
})

onMounted(async () => {
  const profile = await loadTeacherProfile()
  form.value.teacher_name = profile.teacher_name
  form.value.school_name = profile.school_name || '吴忠市吴忠中学'
  form.value.subject = profile.subject
  form.value.grade = profile.grade
})

function generate() {
  if (!form.value.topic) {
    showAlert('请填写课题名称')
    return
  }
  const title = `跟岗研修个人教学设计 · ${form.value.topic}`
  saveAiJob({
    kind: 'lesson',
    title,
    payload: { ...form.value, title },
  })
  router.push('/lesson-plans/output')
}
</script>

<template>
  <main class="sub-page">
    <PageHeader title="个人教学设计" back />
    <div class="page-body">
      <section class="feature-intro orange">
        <h2>跟岗研修个人教学设计</h2>
        <p>吴忠中学“组团帮扶”教师跟岗研修项目 · 泉州一中跟岗基地。生成稿将按汇报用表格式输出。</p>
      </section>
      <button type="button" class="history-link" @click="router.push('/lesson-plans')">查看历史设计 ›</button>
      <section class="form-card">
        <div class="two-col">
          <label>教师姓名<input v-model="form.teacher_name" placeholder="请输入姓名" /></label>
          <label>所在单位<input v-model="form.school_name" placeholder="吴忠市吴忠中学" /></label>
        </div>
        <div class="two-col">
          <label>学科<SuggestInput v-model="form.subject" :options="SUBJECTS" placeholder="可选择或填写" /></label>
          <label>授课年级<SuggestInput v-model="form.grade" :options="GRADES" placeholder="可选择或填写" /></label>
        </div>
        <div class="two-col">
          <label>教材版本<SuggestInput v-model="form.textbook" :options="TEXTBOOKS" placeholder="可选择或填写，例如统编版" /></label>
          <label>课时安排<input v-model.number="form.class_hours" type="number" min="1" /></label>
        </div>
        <label>课题名称<input v-model="form.topic" placeholder="例如：少年中国说" /></label>
        <div class="two-col">
          <label>指导教师<input v-model="form.advisor" placeholder="跟岗指导教师" /></label>
          <label>完成日期<input v-model="form.complete_date" type="date" /></label>
        </div>
        <label>学情说明<textarea v-model="form.student_context" rows="3" placeholder="学生已有基础、认知特点、学习困难"></textarea></label>
        <label>教学要求<textarea v-model="form.requirements" rows="3"></textarea></label>
        <button class="primary-button orange-button" @click="generate">开始生成</button>
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
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  text-align: left;
}
</style>
