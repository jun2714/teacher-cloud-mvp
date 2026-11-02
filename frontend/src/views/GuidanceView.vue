<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { guidanceApi } from '../api'
import PageHeader from '../components/PageHeader.vue'

const route = useRoute()
const router = useRouter()
const items = ref([])
const detail = ref(null)
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const reply = ref('')
const page = ref(1)
const hasMore = ref(false)
const notice = ref('')
let loadVersion = 0
const when = (value) => value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : ''

async function load(append = false) {
  const version = ++loadVersion
  loading.value = true
  error.value = ''
  if (!append) { detail.value = null; items.value = []; page.value = 1; reply.value = ''; notice.value = '' }
  try {
    if (route.params.id) {
      const data = await guidanceApi.detail(route.params.id)
      if (version === loadVersion) detail.value = data
    } else {
      const data = await guidanceApi.list(append ? page.value + 1 : 1)
      if (version !== loadVersion) return
      items.value = append ? [...items.value, ...data.results] : data.results
      page.value = append ? page.value + 1 : 1
      hasMore.value = Boolean(data.next)
    }
  } catch (err) {
    if (version === loadVersion) error.value = err.response?.data?.detail || '加载指导反馈失败，请重试。'
  } finally {
    if (version === loadVersion) loading.value = false
  }
}

async function complete() {
  if (!reply.value.trim()) { error.value = '请先填写本次改进的落实说明。'; return }
  if (saving.value || !detail.value) return
  const id = detail.value.id
  saving.value = true
  error.value = ''
  try {
    const data = await guidanceApi.complete(id, reply.value.trim())
    if (Number(route.params.id) === id) { detail.value = data; notice.value = '落实说明已提交，指导人可查看你的实践反馈。' }
  } catch (err) {
    error.value = err.response?.data?.detail || err.response?.data?.teacher_reply?.[0] || '提交失败，请稍后重试。'
  } finally { saving.value = false }
}

watch(() => route.params.id, () => load(), { immediate: true })
</script>

<template>
  <main class="sub-page guidance-page">
    <PageHeader :title="route.params.id ? '指导反馈' : '我的指导反馈'" back />
    <div class="page-body">
      <p v-if="notice" class="guidance-success" role="status">{{ notice }}</p>
      <p v-if="error" class="guidance-error" role="alert">{{ error }} <button v-if="!detail && !saving" type="button" @click="load()">重新加载</button></p>
      <div v-if="loading && !items.length && !detail" class="loading-card">正在加载指导反馈…</div>
      <template v-else-if="detail">
        <article class="guidance-detail-card">
          <div class="guidance-detail-top"><span>{{ detail.kind_label }}</span><b :class="detail.status">{{ detail.status_label }}</b></div>
          <h2>{{ detail.target_title }}</h2>
          <p class="guidance-from">{{ detail.reviewer_name }} · {{ when(detail.sent_at) }}</p>
          <section v-if="detail.strengths"><h3>值得肯定</h3><p>{{ detail.strengths }}</p></section>
          <section><h3>改进建议</h3><p>{{ detail.suggestions }}</p></section>
          <section v-if="detail.action_plan"><h3>下一步行动</h3><p>{{ detail.action_plan }}</p></section>
          <p v-if="detail.follow_up_date" class="guidance-due">建议跟进时间：{{ detail.follow_up_date }}</p>
          <button v-if="detail.source_link" class="guidance-source" type="button" @click="router.push(detail.source_link)">查看关联成果 →</button>
        </article>
        <section v-if="detail.status === 'done'" class="guidance-detail-card guidance-reply">
          <h3>我的落实说明</h3><p>{{ detail.teacher_reply }}</p><small>{{ when(detail.completed_at) }}</small>
        </section>
        <form v-else class="guidance-detail-card guidance-reply" @submit.prevent="complete">
          <h3>把建议带入教学实践</h3><p class="guidance-reply-help">完成改进后，写下尝试的做法、观察到的变化或下一步想法，让指导人了解你的实践。</p>
          <label for="guidance-reply">落实说明</label><textarea id="guidance-reply" v-model="reply" rows="5" maxlength="5000" required placeholder="例如：我在本次备课中调整了……课堂上观察到……" :disabled="saving"></textarea>
          <button type="submit" class="primary-btn" :disabled="saving">{{ saving ? '正在提交…' : '提交落实说明' }}</button>
        </form>
        <button class="guidance-all" type="button" @click="router.push('/guidance')">查看全部指导反馈</button>
      </template>
      <template v-else-if="!route.params.id">
        <div v-if="!items.length && !error" class="empty-card">暂未收到指导反馈。收到后，可在这里查看建议并记录落实情况。</div>
        <button v-for="item in items" :key="item.id" class="guidance-list-card" type="button" @click="router.push(`/guidance/${item.id}`)">
          <div class="guidance-detail-top"><span>{{ item.kind_label }}</span><b :class="item.status">{{ item.status_label }}</b></div><h2>{{ item.target_title }}</h2><p>{{ item.suggestions }}</p><small>{{ item.reviewer_name }} · {{ when(item.sent_at) }}</small>
        </button>
        <button v-if="hasMore" class="guidance-all" type="button" :disabled="loading" @click="load(true)">{{ loading ? '加载中…' : '加载更多' }}</button>
      </template>
    </div>
  </main>
</template>

<style scoped>
.guidance-detail-card,.guidance-list-card { width:100%; text-align:left; background:#fff; border:1px solid var(--line); border-radius:16px; padding:20px; margin-bottom:16px; color:var(--text); }
.guidance-detail-top { display:flex; align-items:center; justify-content:space-between; gap:12px; font-size:12px; color:#61748f; }
.guidance-detail-top b { font-weight:500; border-radius:5px; padding:3px 8px; }
.guidance-detail-top .sent { color:#956015; background:#fff4df; }.guidance-detail-top .done { color:#217758; background:#e9f7f0; }
.guidance-detail-card h2,.guidance-list-card h2 { margin:14px 0 10px; font-size:19px; line-height:1.6; overflow-wrap:anywhere; }
.guidance-from { color:#61748f; font-size:12px; margin:0 0 22px; }
.guidance-detail-card section { padding-top:18px; border-top:1px solid var(--line); margin-top:18px; }
.guidance-detail-card h3 { font-size:15px; margin:0 0 10px; color:#203b60; }
.guidance-detail-card p { line-height:1.9; font-size:14px; white-space:pre-wrap; overflow-wrap:anywhere; }
.guidance-due { color:#61748f; font-size:12px!important; padding:12px; background:#f4f8ff; border-radius:7px; margin-top:20px; }
.guidance-source,.guidance-all { color:#1769dc; font-size:14px; background:#eef5ff; border:0; border-radius:8px; padding:12px; min-height:44px; }
.guidance-source { margin-top:14px; }.guidance-all { width:100%; }
.guidance-reply-help { color:#61748f; font-size:13px!important; }
.guidance-reply label { display:block; font-size:13px; margin:18px 0 8px; }
.guidance-reply textarea { border:1px solid var(--line); border-radius:8px; width:100%; padding:12px; font:inherit; font-size:14px; line-height:1.8; box-sizing:border-box; resize:vertical; }
.guidance-reply .primary-btn { margin-top:14px; width:100%; min-height:44px; padding:12px 16px; border:0; border-radius:9px; background:#1769dc; color:#fff; font:inherit; font-size:15px; font-weight:600; cursor:pointer; }.guidance-reply small { color:#61748f; font-size:12px; }
.guidance-list-card>p { color:#526580; font-size:13px; line-height:1.8; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.guidance-list-card>small { display:block; color:#61748f; margin-top:14px; font-size:12px; }
.guidance-error,.guidance-success { border-radius:8px; padding:12px; font-size:13px; line-height:1.7; margin-bottom:14px; }
.guidance-error { color:#aa3535; background:#fff1f0; }.guidance-error button { color:inherit; text-decoration:underline; border:0; background:none; }
.guidance-success { color:#217758; background:#e9f7f0; }
button:disabled { opacity:.6; cursor:wait; }
</style>
