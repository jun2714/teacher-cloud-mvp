<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { communityApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import SuggestInput from '../components/SuggestInput.vue'
import { GRADES, SUBJECTS } from '../constants/options'
import { loadTeacherProfile } from '../composables/useTeacherProfile'
import { errorMessage, showAlert } from '../utils/dialog'

const router = useRouter()
const saving = ref(false)
const form = ref({ title: '', content: '', subject: '', grade: '', tags: '', ask_ai: true })

onMounted(async () => {
  const profile = await loadTeacherProfile()
  form.value.subject = profile.subject
  form.value.grade = profile.grade
})

async function submit() {
  if (!form.value.title || !form.value.content) {
    showAlert('请填写标题和问题详情')
    return
  }
  saving.value = true
  try {
    const payload = { ...form.value, tags: form.value.tags.split(/[，,、\s]+/).filter(Boolean) }
    const { data } = await communityApi.create(payload)
    if (payload.ask_ai && data.ai_failed) {
      await showAlert('问题已发布，但 AI 参考回答暂时无法生成。可在详情里继续邀请同事作答。', 'error')
    }
    router.replace(`/questions/${data.id}`)
  } catch (e) {
    showAlert(errorMessage(e, '发布失败'), 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <main class="sub-page">
    <PageHeader title="发布疑惑" back />
    <div class="page-body">
      <section class="form-card">
        <label>问题标题<input v-model="form.title" placeholder="用一句话描述你的教学疑惑" /></label>
        <label>问题详情<textarea v-model="form.content" rows="10" placeholder="说明课堂场景、已经尝试的方法，以及希望得到哪方面建议"></textarea></label>
        <div class="two-col">
          <label>学科<SuggestInput v-model="form.subject" :options="SUBJECTS" placeholder="可选择或填写" /></label>
          <label>年级<SuggestInput v-model="form.grade" :options="GRADES" placeholder="可选择或填写" /></label>
        </div>
        <label>标签<input v-model="form.tags" placeholder="课堂参与, 小组合作" /></label>
        <label class="switch-row">
          <span><b>邀请 AI 提供参考回答</b><small>AI回答会单独标记，教师仍可继续补充</small></span>
          <input v-model="form.ask_ai" type="checkbox" />
        </label>
        <button class="primary-button" :disabled="saving" @click="submit">{{ saving ? '发布中…' : '发布问题' }}</button>
      </section>
    </div>
  </main>
</template>
