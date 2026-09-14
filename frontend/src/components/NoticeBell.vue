<script setup>
import { storeToRefs } from 'pinia'
import { useRouter } from 'vue-router'
import { useNoticeStore } from '../stores/notices'

const router = useRouter()
const notices = useNoticeStore()
const { unread } = storeToRefs(notices)

defineProps({
  light: { type: Boolean, default: false },
})
</script>

<template>
  <button class="notice-bell" :class="{ light }" type="button" aria-label="消息通知" @click="router.push('/notices')">
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 9a6 6 0 0 1 12 0c0 4 1.5 5.5 1.5 5.5H4.5S6 13 6 9z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
      <path d="M10 18a2 2 0 0 0 4 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </svg>
    <i v-if="unread">{{ unread > 9 ? '9+' : unread }}</i>
  </button>
</template>

<style scoped>
.notice-bell {
  position: relative;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  background: #e8f1ff;
  color: #1a6dff;
  display: grid;
  place-items: center;
  padding: 0;
}
.notice-bell.light {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}
.notice-bell svg {
  width: 18px;
  height: 18px;
}
.notice-bell i {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  border-radius: 999px;
  background: #f04438;
  color: #fff;
  font-size: 9px;
  font-style: normal;
  font-weight: 800;
  line-height: 14px;
  text-align: center;
}
</style>
