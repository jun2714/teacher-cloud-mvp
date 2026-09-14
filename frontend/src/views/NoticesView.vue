<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { noticeApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import { useNoticeStore } from '../stores/notices'

const router = useRouter()
const notices = useNoticeStore()
const items = ref([])
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    items.value = await noticeApi.list()
    await notices.refresh({ silent: true })
  } finally {
    loading.value = false
  }
}

async function open(item) {
  if (!item.is_read) {
    await noticeApi.markRead([item.id])
    item.is_read = true
    await notices.refresh({ silent: true })
  }
  if (item.link) router.push(item.link)
}

async function markAll() {
  await notices.markAllRead()
  items.value.forEach((item) => { item.is_read = true })
}

onMounted(load)
</script>

<template>
  <main class="sub-page">
    <PageHeader title="消息通知" back />
    <div class="page-body">
      <button v-if="items.some((item) => !item.is_read)" class="text-link all-read" type="button" @click="markAll">全部标为已读</button>
      <div v-if="loading" class="loading-card">加载中…</div>
      <article v-else-if="!items.length" class="empty-card">还没有通知</article>
      <article
        v-for="item in items"
        :key="item.id"
        class="notice-card"
        :class="{ unread: !item.is_read }"
        role="button"
        @click="open(item)"
      >
        <b>{{ item.title }}</b>
        <p v-if="item.body">{{ item.body }}</p>
        <small>{{ new Date(item.created_at).toLocaleString() }}</small>
      </article>
    </div>
  </main>
</template>

<style scoped>
.all-read {
  margin-bottom: 10px;
}
.notice-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px 14px;
  margin-bottom: 10px;
}
.notice-card.unread {
  background: #f4f8ff;
  border-color: #d6e6ff;
}
.notice-card b {
  display: block;
  font-size: 15px;
}
.notice-card p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.5;
}
.notice-card small {
  display: block;
  margin-top: 8px;
  font-size: 12px;
  color: var(--muted);
}
</style>
