<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useAuthStore } from '../stores/auth'
import { useNoticeStore } from '../stores/notices'
import chatIcon from '../assets/images/confused.webp'
import chatIcon1 from '../assets/images/confused1.webp'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notices = useNoticeStore()
const { unread } = storeToRefs(notices)
const showNav = computed(() => !route.meta.hideNav)

const items = [
  { name: 'home', label: '首页', icon: 'home' },
  { name: 'notes', label: '教研笔记', icon: 'notes' },
  { name: 'community', label: '疑惑交流', icon: 'chat' },
  { name: 'mine', label: '我的', icon: 'user' },
]

const fabTo = computed(() => {
  if (route.name === 'notes') return '/notes/new'
  if (route.name === 'community') return '/questions/new'
  return ''
})

onMounted(() => {
  auth.fetchMe()
  notices.start()
})
onUnmounted(() => notices.stop())
</script>

<template>
  <div class="app-frame" :class="{ 'with-nav': showNav }">
    <router-view />
    <button
      v-if="fabTo"
      class="fab"
      type="button"
      aria-label="新建"
      @click="router.push(fabTo)"
    >＋</button>
    <nav v-if="showNav" class="bottom-nav">
      <button
        v-for="item in items"
        :key="item.name"
        :class="{ active: route.name === item.name }"
        @click="item.name === 'community' ? router.push({ name: 'community', query: {} }) : router.push({ name: item.name })"
      >
        <span class="nav-icon">
          <svg v-if="item.icon === 'home'" viewBox="0 0 24 24">
            <path d="M4 10.5L12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5z" />
          </svg>
          <svg v-else-if="item.icon === 'notes'" viewBox="0 0 24 24">
            <path d="M7 3h8l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" />
            <path d="M15 3v4h4M9 12h6M9 16h4" />
          </svg>
          <img v-else-if="item.icon === 'chat'" class="nav-img" :src="route.name === item.name ? chatIcon1 : chatIcon" alt="" />
          <svg v-else viewBox="0 0 24 24">
            <circle cx="12" cy="8" r="3.5" />
            <path d="M5 19c1.5-3.5 4-5 7-5s5.5 1.5 7 5" />
          </svg>
          <i v-if="item.icon === 'user' && unread" class="nav-badge">{{ unread > 9 ? '9+' : unread }}</i>
        </span>
        <span>{{ item.label }}</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.nav-img {
  width: 22px;
  height: 22px;
  object-fit: contain;
  display: block;
  border-radius: 6px;
}

.bottom-nav button:not(.active) .nav-img {
  opacity: 0.55;
  filter: grayscale(0.3);
}

.nav-icon {
  position: relative;
}

.nav-badge {
  position: absolute;
  top: -4px;
  right: -8px;
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
