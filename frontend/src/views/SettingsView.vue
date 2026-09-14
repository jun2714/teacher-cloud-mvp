<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '../components/PageHeader.vue'
import { useAuthStore } from '../stores/auth'
import { authApi } from '../api'
import { errorMessage, showAlert } from '../utils/dialog'

const router = useRouter()
const auth = useAuthStore()
const notifyLesson = ref(true)
const notifyCommunity = ref(true)
const tip = ref('')
const savingPwd = ref(false)
const pwd = ref({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

function applyNotifyFromUser() {
  const profile = auth.user?.profile || {}
  notifyLesson.value = profile.notify_lesson !== false
  notifyCommunity.value = profile.notify_community !== false
}

onMounted(async () => {
  if (!auth.user) await auth.fetchMe()
  applyNotifyFromUser()
})

async function persistNotify() {
  try {
    await auth.updateProfile({
      notify_lesson: notifyLesson.value,
      notify_community: notifyCommunity.value,
    })
    tip.value = '设置已保存'
  } catch (e) {
    showAlert(errorMessage(e, '保存失败'), 'error')
    applyNotifyFromUser()
  }
  setTimeout(() => { tip.value = '' }, 1500)
}

function clearCache() {
  const keep = ['access_token', 'refresh_token']
  const snapshot = {}
  keep.forEach((k) => {
    const v = localStorage.getItem(k)
    if (v != null) snapshot[k] = v
  })
  localStorage.clear()
  Object.entries(snapshot).forEach(([k, v]) => localStorage.setItem(k, v))
  applyNotifyFromUser()
  tip.value = '本地缓存已清理'
  setTimeout(() => { tip.value = '' }, 1500)
}

async function changePassword() {
  if (!pwd.value.old_password || !pwd.value.new_password) {
    showAlert('请填写原密码和新密码')
    return
  }
  if (pwd.value.new_password.length < 6) {
    showAlert('新密码至少 6 位')
    return
  }
  if (pwd.value.new_password !== pwd.value.confirm_password) {
    showAlert('两次输入的新密码不一致')
    return
  }
  savingPwd.value = true
  try {
    await authApi.changePassword(pwd.value)
    pwd.value = { old_password: '', new_password: '', confirm_password: '' }
    await showAlert('密码已修改，请使用新密码重新登录')
    await auth.logout()
    router.replace('/login')
  } catch (e) {
    showAlert(errorMessage(e, '修改失败'), 'error')
  } finally {
    savingPwd.value = false
  }
}
</script>

<template>
  <main class="sub-page">
    <PageHeader title="设置" back />
    <div class="page-body">
      <section class="settings-card">
        <h3>账号安全</h3>
        <div class="pwd-form">
          <label>原密码<input v-model="pwd.old_password" type="password" autocomplete="current-password" placeholder="请输入原密码" /></label>
          <label>新密码<input v-model="pwd.new_password" type="password" autocomplete="new-password" placeholder="至少 6 位" /></label>
          <label>确认新密码<input v-model="pwd.confirm_password" type="password" autocomplete="new-password" placeholder="再输入一次新密码" /></label>
          <button class="primary-button" type="button" :disabled="savingPwd" @click="changePassword">
            {{ savingPwd ? '提交中…' : '修改密码' }}
          </button>
        </div>
      </section>

      <section class="settings-card">
        <h3>消息通知</h3>
        <label class="settings-row">
          <div>
            <b>教学设计提醒</b>
            <span>教案、报告、听评课生成完成后，顶部弹出并显示红点</span>
          </div>
          <input v-model="notifyLesson" type="checkbox" @change="persistNotify" />
        </label>
        <label class="settings-row">
          <div>
            <b>社区互动提醒</b>
            <span>收到回答或点赞时，顶部弹出并显示红点</span>
          </div>
          <input v-model="notifyCommunity" type="checkbox" @change="persistNotify" />
        </label>
      </section>

      <section class="settings-card">
        <h3>通用</h3>
        <button class="settings-row action" type="button" @click="clearCache">
          <div>
            <b>清理本地缓存</b>
            <span>不影响登录状态与云端数据</span>
          </div>
          <i>›</i>
        </button>
      </section>

      <section class="settings-card about">
        <h3>关于</h3>
        <div class="about-row">
          <span>应用名称</span>
          <b>教研云</b>
        </div>
        <div class="about-row">
          <span>当前版本</span>
          <b>v0.1.0</b>
        </div>
        <div class="about-row">
          <span>当前账号</span>
          <b>{{ auth.user?.username || '—' }}</b>
        </div>
        <p>教师专业成长平台 · 支持备课、教研笔记、听评课与疑惑交流。</p>
      </section>

      <p v-if="tip" class="settings-tip">{{ tip }}</p>
    </div>
  </main>
</template>

<style scoped>
.settings-card {
  background: #fff;
  border: 1px solid #e8ecf2;
  border-radius: 16px;
  padding: 6px 0;
  margin-bottom: 14px;
  overflow: hidden;
}

.settings-card h3 {
  margin: 0;
  padding: 12px 16px 6px;
  font-size: 13px;
  font-weight: 600;
  color: #8a93a3;
}

.settings-row {
  width: 100%;
  min-height: 64px;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  border: 0;
  border-top: 1px solid #eef1f6;
  background: #fff;
  text-align: left;
  color: #1a2332;
}

.settings-card > .settings-row:first-of-type,
.settings-card h3 + .settings-row {
  border-top: 0;
}

.settings-row div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.settings-row b {
  font-size: 15px;
  font-weight: 600;
}

.settings-row span {
  font-size: 12px;
  color: #8a93a3;
  line-height: 1.4;
}

.settings-row input[type='checkbox'] {
  width: 44px;
  height: 24px;
  accent-color: #1a6dff;
  flex-shrink: 0;
}

.settings-row.action:active {
  background: #f8fafc;
}

.settings-row i {
  font-style: normal;
  font-size: 22px;
  color: #c0c6d0;
}

.about .about-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-top: 1px solid #eef1f6;
  font-size: 14px;
}

.about h3 + .about-row {
  border-top: 0;
}

.about .about-row span {
  color: #8a93a3;
}

.about .about-row b {
  color: #1a2332;
  font-weight: 600;
}

.about > p {
  margin: 0;
  padding: 8px 16px 16px;
  font-size: 12px;
  line-height: 1.55;
  color: #8a93a3;
}

.settings-tip {
  margin: 4px 0 0;
  text-align: center;
  font-size: 13px;
  color: #12b76a;
}

.pwd-form {
  padding: 4px 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pwd-form label {
  display: block;
  font-size: 13px;
  font-weight: 700;
}

.pwd-form input {
  width: 100%;
  margin-top: 7px;
  border: 1px solid #e8ecf2;
  border-radius: 12px;
  padding: 11px 12px;
  background: #f8fafc;
}
</style>
