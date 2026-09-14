<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { communityApi } from '../api'
import PageHeader from '../components/PageHeader.vue'

const router = useRouter()
const route = useRoute()
const questions = ref([])
const loading = ref(true)
const scope = ref('all')

const solved = computed(() => questions.value.filter((q) => q.status === 'solved').length)
const pending = computed(() => questions.value.filter((q) => q.status !== 'solved').length)
const emptyText = computed(() => {
  if (scope.value === 'mine') return '还没有你发布的问题'
  if (scope.value === 'answered') return '还没有你回答过的问题'
  return '还没有问题，点击右下角发布一条'
})

async function load() {
  loading.value = true
  try {
    const params = scope.value === 'all' ? undefined : { scope: scope.value }
    questions.value = await communityApi.list(params)
  } finally {
    loading.value = false
  }
}

function setScope(next) {
  router.replace({ path: '/community', query: next === 'all' ? {} : { scope: next } })
}

async function like(q, e) {
  e.stopPropagation()
  const { data } = await communityApi.toggleQuestionLike(q.id)
  q.is_liked = data.liked
  q.like_count = data.like_count
}

watch(
  () => route.query.scope,
  (value) => {
    scope.value = value === 'mine' || value === 'answered' ? value : 'all'
    load()
  },
  { immediate: true },
)
</script>

<template>
  <main class="sub-page">
    <PageHeader title="疑惑交流" />
    <div class="page-body">
      <div class="intro">
        <h2>疑惑交流</h2>
        <p>新课标、新课改、新高考实践中的疑惑，与同行交流探讨</p>
      </div>
      <div class="mode-tabs">
        <button type="button" :class="{ active: scope === 'all' }" @click="setScope('all')">全部</button>
        <button type="button" :class="{ active: scope === 'mine' }" @click="setScope('mine')">我的提问</button>
        <button type="button" :class="{ active: scope === 'answered' }" @click="setScope('answered')">我的回答</button>
      </div>
      <div class="stat-grid">
        <div><b>{{ questions.length }}</b><span>问题数</span></div>
        <div><b>{{ solved }}</b><span>已解答</span></div>
        <div><b>{{ pending }}</b><span>待解答</span></div>
      </div>
      <div v-if="loading" class="loading-card">加载中…</div>
      <article v-else-if="!questions.length" class="empty-card">{{ emptyText }}</article>
      <article v-for="q in questions" :key="q.id" class="question-card" @click="router.push(`/questions/${q.id}`)">
        <div class="author-row">
          <span class="avatar">
            <img v-if="q.author_info.profile?.avatar_url" :src="q.author_info.profile.avatar_url" alt="" />
            <template v-else>{{ q.author_info.profile?.avatar_text || q.author_info.display_name?.[0] || '师' }}</template>
          </span>
          <div>
            <b>{{ q.author_info.display_name }}</b>
            <time>{{ new Date(q.created_at).toLocaleDateString() }}</time>
          </div>
        </div>
        <h3>{{ q.title }}</h3>
        <p>{{ q.content }}</p>
        <div class="tag-list"><span v-for="tag in q.tags" :key="tag">{{ tag }}</span></div>
        <p v-if="q.ai_failed" class="ai-fail-tip">AI 参考回答生成失败，详情里可查看说明</p>
        <footer>
          <span>💬 {{ q.answer_count }} 回答</span>
          <button :class="{ liked: q.is_liked }" @click="like(q, $event)">♡ {{ q.like_count }} 赞同</button>
          <em :class="q.status">{{ q.status_label }}</em>
        </footer>
      </article>
    </div>
  </main>
</template>

<style scoped>
.ai-fail-tip {
  margin: 0 0 8px;
  font-size: 12px;
  color: #d97706;
}
</style>
