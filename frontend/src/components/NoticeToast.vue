<script setup>
import { watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useNoticeStore } from '../stores/notices'
import { noticeApi } from '../api'

const router = useRouter()
const notices = useNoticeStore()
const { toast } = storeToRefs(notices)
let hideTimer = null

watch(toast, (val) => {
  if (hideTimer) {
    clearTimeout(hideTimer)
    hideTimer = null
  }
  if (val) {
    hideTimer = setTimeout(() => notices.clearToast(), 4500)
  }
})

async function open() {
  const item = toast.value
  notices.clearToast()
  if (!item) return
  if (item.id) {
    try { await noticeApi.markRead([item.id]) } catch { /* ignore */ }
    notices.refresh({ silent: true })
  }
  if (item.link) router.push(item.link)
  else router.push('/notices')
}
</script>

<template>
  <button v-if="toast" class="notice-toast" type="button" @click="open">
    <b>{{ toast.title }}</b>
    <small>{{ toast.body || '点击查看' }}</small>
  </button>
</template>

<style scoped>
.notice-toast {
  position: fixed;
  left: 14px;
  right: 14px;
  top: calc(12px + env(safe-area-inset-top));
  z-index: 80;
  border: 0;
  border-radius: 14px;
  padding: 12px 14px;
  background: #1a2332;
  color: #fff;
  text-align: left;
  box-shadow: 0 12px 28px rgba(26, 35, 50, 0.28);
  animation: toast-in 0.25s ease;
}
.notice-toast b {
  display: block;
  font-size: 14px;
}
.notice-toast small {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.72);
}
@keyframes toast-in {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: none; }
}
</style>
