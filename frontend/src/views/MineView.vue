<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../api'
import { useAuthStore } from '../stores/auth'
import { teacherProfileFields } from '../composables/useTeacherProfile'
import NoticeBell from '../components/NoticeBell.vue'

const router = useRouter()
const auth = useAuthStore()
const profile = computed(() => teacherProfileFields(auth.user))
const stats = ref({
  learning_days: 0,
  notes: 0,
  questions: 0,
  solved_questions: 0,
})

onMounted(async () => {
  await auth.fetchMe()
  stats.value = (await authApi.stats()).data
})

async function logout() {
  await auth.logout()
  router.replace('/login')
}

const accountMenus = [
  { to: '/profile', label: '个人信息', icon: 'profile' },
  { to: '/settings', label: '设置', icon: 'settings' },
]

const menus = [
  { to: '/notes', label: '我的笔记', icon: 'notes' },
  { to: '/community?scope=mine', label: '我的问题与回答', icon: 'qa' },
  { to: '/lesson-plans', label: '我的教学设计', icon: 'design' },
  { to: '/lesson-reviews', label: '我的听评课报告', icon: 'review' },
]
</script>

<template>
  <main class="mine">
    <header class="mine-title">
      我的
      <NoticeBell class="mine-bell" />
    </header>

    <section class="mine-hero">
      <div class="mine-user">
        <span class="mine-avatar">
          <img v-if="auth.user?.profile?.avatar_url" :src="auth.user.profile.avatar_url" alt="" />
          <template v-else>{{ auth.user?.profile?.avatar_text || profile.display_name?.[0] || '师' }}</template>
        </span>
        <div class="mine-user-meta">
          <h2>{{ profile.display_name || '教师用户' }}</h2>
          <p>
            {{ profile.school_name || '未填写学校' }}
            ·
            {{ profile.department || '未填写教研组' }}
          </p>
        </div>
      </div>

      <div class="mine-stats">
        <div>
          <b>{{ stats.learning_days }}</b>
          <span>学习天数</span>
        </div>
        <div>
          <b>{{ stats.notes }}</b>
          <span>教研笔记</span>
        </div>
        <div>
          <b>{{ stats.solved_questions }}</b>
          <span>已解决问题</span>
        </div>
      </div>
    </section>

    <div class="mine-body">
      <section class="mine-menu">
        <button
          v-for="item in accountMenus"
          :key="item.to"
          type="button"
          @click="router.push(item.to)"
        >
          <span class="mine-menu-icon">
            <svg v-if="item.icon === 'profile'" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="3.5" stroke="currentColor" stroke-width="1.8" />
              <path d="M5 19c1.5-3.5 4-5 7-5s5.5 1.5 7 5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="1.8" />
              <path d="M12 4.5v1.2M12 18.3v1.2M4.5 12h1.2M18.3 12h1.2M6.4 6.4l.9.9M16.7 16.7l.9.9M6.4 17.6l.9-.9M16.7 7.3l.9-.9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </span>
          <b>{{ item.label }}</b>
          <i>›</i>
        </button>
      </section>

      <section class="mine-menu">
        <button
          v-for="item in menus"
          :key="item.to"
          type="button"
          @click="router.push(item.to)"
        >
          <span class="mine-menu-icon">
            <svg v-if="item.icon === 'notes'" viewBox="0 0 24 24" fill="none">
              <path d="M7 3h8l4 4v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z" stroke="currentColor" stroke-width="1.8" />
              <path d="M15 3v4h4M9 12h6M9 16h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
            <svg v-else-if="item.icon === 'qa'" viewBox="0 0 24 24" fill="none">
              <path d="M5 6.5A2.5 2.5 0 0 1 7.5 4h9A2.5 2.5 0 0 1 19 6.5v6A2.5 2.5 0 0 1 16.5 15H11l-4 3v-3H7.5A2.5 2.5 0 0 1 5 12.5v-6z" stroke="currentColor" stroke-width="1.8" />
            </svg>
            <svg v-else-if="item.icon === 'design'" viewBox="0 0 24 24" fill="none">
              <path d="M5 19l1.2-4.6L16.6 4A2 2 0 0 1 19.4 6.8L9 17.2 5 19z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
              <path d="M13.5 7.5l3 3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none">
              <path d="M4 7h16M4 12h10M4 17h7" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
              <circle cx="18" cy="16" r="3" stroke="currentColor" stroke-width="1.8" />
            </svg>
          </span>
          <b>{{ item.label }}</b>
          <i>›</i>
        </button>
      </section>

      <section class="mine-version">
        <strong>教研云 v0.1.0</strong>
        <span>教师专业成长平台</span>
      </section>

      <button class="mine-logout" type="button" @click="logout">退出登录</button>
    </div>
  </main>
</template>

<style scoped>
.mine {
  min-height: 100%;
  background: #f4f6fa;
  padding-bottom: 20px;
  animation: mine-in 0.35s ease;
}

@keyframes mine-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: none; }
}

.mine-title {
  height: 52px;
  display: grid;
  place-items: center;
  font-size: 17px;
  font-weight: 700;
  color: #1a2332;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e8ecf2;
  position: sticky;
  top: 0;
  z-index: 20;
  backdrop-filter: blur(16px);
}

.mine-bell {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
}

.mine-hero {
  margin: 14px 14px 0;
  padding: 20px 16px 16px;
  border-radius: 20px;
  color: #fff;
  background: linear-gradient(145deg, #1a6dff 0%, #2f7bff 48%, #5b8dff 100%);
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.22);
  position: relative;
  overflow: hidden;
}

.mine-hero::after {
  content: "";
  position: absolute;
  right: -36px;
  top: -40px;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  pointer-events: none;
}

.mine-user {
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  z-index: 1;
}

.mine-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.75);
  background: rgba(255, 255, 255, 0.18);
  display: grid;
  place-items: center;
  font-size: 22px;
  font-weight: 800;
  flex-shrink: 0;
  overflow: hidden;
}

.mine-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.mine-user-meta {
  min-width: 0;
  text-align: left;
}

.mine-user-meta h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.25;
}

.mine-user-meta p {
  margin: 5px 0 0;
  font-size: 12px;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.82);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.mine-stats {
  position: relative;
  z-index: 1;
  margin-top: 16px;
  padding: 14px 8px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 4px 14px rgba(13, 79, 214, 0.12);
}

.mine-stats div {
  text-align: center;
}

.mine-stats b {
  display: block;
  font-size: 20px;
  font-weight: 800;
  color: #1a6dff;
  line-height: 1.2;
}

.mine-stats span {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #8a93a3;
}

.mine-body {
  padding: 18px 14px 8px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mine-menu {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 16px;
  overflow: hidden;
}

.mine-menu button {
  width: 100%;
  min-height: 64px;
  border: 0;
  border-bottom: 1px solid #eef1f6;
  background: #fff;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  color: #1a2332;
  text-align: left;
}

.mine-menu button:last-child {
  border-bottom: 0;
}

.mine-menu button:active {
  background: #f8fafc;
}

.mine-menu-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: #e8f1ff;
  color: #1a6dff;
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.mine-menu-icon svg {
  width: 20px;
  height: 20px;
}

.mine-menu b {
  flex: 1;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.mine-menu i {
  font-style: normal;
  font-size: 22px;
  color: #c0c6d0;
  line-height: 1;
  padding-left: 4px;
}

.mine-version {
  margin-top: 0;
  padding: 16px 16px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid #e8ecf2;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mine-version strong {
  font-size: 13px;
  font-weight: 600;
  color: #5c6678;
}

.mine-version span {
  font-size: 12px;
  color: #8a93a3;
  line-height: 1.45;
}

.mine-logout {
  width: 100%;
  margin-top: 0;
  min-height: 52px;
  border: 1px solid #e8ecf2;
  border-radius: 14px;
  background: #fff;
  color: #f04438;
  font-size: 15px;
  font-weight: 600;
  text-align: left;
  padding: 0 16px;
}

.mine-logout:active {
  background: #fff5f5;
}
</style>
