<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { lessonApi, reportsApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import { errorMessage, showAlert, showConfirm } from '../utils/dialog'

const route = useRoute()
const router = useRouter()
const kind = computed(() => route.meta.kind || 'lesson')
const items = ref([])
const loading = ref(true)
const removingId = ref(null)

const meta = computed(() => {
  if (kind.value === 'report') {
    return {
      title: '我的总结报告',
      createTo: '/reports/generate',
      createLabel: '生成总结',
      empty: '还没有生成总结报告',
      orange: false,
    }
  }
  if (kind.value === 'review') {
    return {
      title: '我的听评课报告',
      createTo: '/lesson-review',
      createLabel: '新建听评课',
      empty: '还没有生成听评课报告',
      orange: false,
    }
  }
  return {
    title: '我的教学设计',
    createTo: '/lesson-design',
    createLabel: '新建设计',
    empty: '还没有生成教学设计',
    orange: true,
  }
})

onMounted(async () => {
  try {
    if (kind.value === 'report') items.value = await reportsApi.list()
    else if (kind.value === 'review') items.value = await lessonApi.listReviews()
    else items.value = await lessonApi.list()
  } finally {
    loading.value = false
  }
})

function open(item) {
  if (kind.value === 'report') router.push(`/reports/${item.id}`)
  else if (kind.value === 'review') router.push(`/lesson-reviews/${item.id}`)
  else router.push(`/lesson-plans/${item.id}`)
}

function subtitle(item) {
  const date = new Date(item.created_at).toLocaleDateString()
  if (kind.value === 'report') {
    const n = item.source_note_ids?.length || 0
    return `${n} 篇笔记 · ${date}`
  }
  if (kind.value === 'review') {
    const bits = [item.subject, item.grade, item.course_teacher].filter(Boolean)
    return `${bits.join(' · ') || '听评课'} · ${date}`
  }
  const bits = [item.subject, item.grade, item.topic].filter(Boolean)
  return `${bits.join(' · ') || '教学设计'} · ${date}`
}

async function remove(item) {
  const ok = await showConfirm(`删除「${item.title || '未命名'}」？删除后不可恢复。`)
  if (!ok) return
  removingId.value = item.id
  try {
    if (kind.value === 'report') await reportsApi.remove(item.id)
    else if (kind.value === 'review') await lessonApi.removeReview(item.id)
    else await lessonApi.remove(item.id)
    items.value = items.value.filter((row) => row.id !== item.id)
  } catch (e) {
    showAlert(errorMessage(e, '删除失败'), 'error')
  } finally {
    removingId.value = null
  }
}
</script>

<template>
  <main class="sub-page">
    <PageHeader :title="meta.title" back />
    <div class="page-body">
      <button class="primary-button" :class="{ 'orange-button': meta.orange }" @click="router.push(meta.createTo)">
        {{ meta.createLabel }}
      </button>
      <h3 class="list-label">历史记录</h3>
      <div v-if="loading" class="loading-card">加载中…</div>
      <article v-else-if="!items.length" class="empty-card">{{ meta.empty }}</article>
      <article
        v-for="item in items"
        :key="item.id"
        class="mini-report is-link"
        role="button"
        tabindex="0"
        @click="open(item)"
      >
        <span>▤</span>
        <div>
          <b>{{ item.title }}</b>
          <small>{{ subtitle(item) }}</small>
        </div>
        <div class="mini-side">
          <em>已完成</em>
          <button
            class="mini-del"
            type="button"
            :disabled="removingId === item.id"
            @click.stop="remove(item)"
          >{{ removingId === item.id ? '删除中' : '删除' }}</button>
        </div>
      </article>
    </div>
  </main>
</template>

<style scoped>
.primary-button {
  margin-bottom: 6px;
}

.mini-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
}

.mini-del {
  border: 0;
  background: none;
  color: #f04438;
  font-size: 12px;
  font-weight: 700;
  padding: 0;
}
</style>
