<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useSmsCaptcha } from '../composables/useSmsCaptcha'
import { showAlert } from '../utils/dialog'
import logoImg from '../assets/icon/teach.webp'
import bgImg from '../assets/images/bg.webp'

const router = useRouter()
const auth = useAuthStore()

const phone = ref('')
const smsCode = ref('')
const loading = ref(false)
const error = ref('')
const tip = ref('')
const {
  captchaImage,
  captchaCode,
  sending,
  cooldown,
  loadCaptcha,
  sendSmsCode,
} = useSmsCaptcha()

async function sendCode() {
  error.value = ''
  tip.value = ''
  try {
    const data = await sendSmsCode(phone.value.trim())
    tip.value = data.demo_code
      ? `验证码已发送（演示：${data.demo_code}）`
      : '验证码已发送，请注意查收'
  } catch (e) {
    error.value = e.message || '验证码发送失败'
  }
}

async function submit() {
  error.value = ''
  tip.value = ''
  if (!/^1\d{10}$/.test(phone.value)) {
    error.value = '请输入正确的手机号'
    return
  }
  if (!smsCode.value.trim()) {
    error.value = '请输入短信验证码'
    return
  }
  loading.value = true
  try {
    const data = await auth.register({
      phone: phone.value.trim(),
      sms_code: smsCode.value.trim(),
    })
    if (data?.existing) {
      await showAlert('该手机号已注册，已为您登录。')
    } else {
      await showAlert('注册成功。可用该手机号登录，初始密码 123456，请到「我的 → 设置」修改。')
    }
    router.replace('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page" :style="{ backgroundImage: `url(${bgImg})` }">
    <header class="login-brand">
      <img class="login-logo" :src="logoImg" alt="教研云" />
      <h1>教研云</h1>
      <i class="brand-line" aria-hidden="true" />
      <p>教师专业成长与协作教研平台</p>
    </header>

    <form class="login-card" @submit.prevent="submit">
      <div class="auth-tabs" role="tablist">
        <button type="button" class="auth-tab" @click="router.push('/login')">登录</button>
        <button type="button" class="auth-tab is-active">注册</button>
      </div>

      <label class="field">
        <span>手机号</span>
        <div class="field-box">
          <svg class="leading" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="7" y="3" width="10" height="18" rx="2" stroke="#3b82f6" stroke-width="1.8" />
            <circle cx="12" cy="17" r="1" fill="#3b82f6" />
          </svg>
          <input v-model="phone" inputmode="numeric" maxlength="11" autocomplete="tel" placeholder="请输入手机号" />
        </div>
      </label>

      <label class="field">
        <span>图形验证码</span>
        <div class="field-box captcha-row">
          <input v-model="captchaCode" maxlength="6" placeholder="请输入图中字符" />
          <button type="button" class="captcha-img" title="点击刷新" @click="loadCaptcha()">
            <img v-if="captchaImage" :src="captchaImage" alt="验证码" />
            <span v-else>加载中</span>
          </button>
        </div>
      </label>

      <label class="field">
        <span>短信验证码</span>
        <div class="field-box sms-row">
          <input v-model="smsCode" inputmode="numeric" maxlength="6" placeholder="请输入验证码" />
          <button
            type="button"
            class="sms-btn"
            :disabled="sending || cooldown > 0"
            @click="sendCode"
          >
            {{ cooldown > 0 ? `${cooldown}s` : sending ? '发送中' : '获取验证码' }}
          </button>
        </div>
      </label>

      <p class="hint">新号码将自动注册，初始密码 123456。已注册号码验证通过后直接登录。</p>

      <p v-if="error" class="form-error">{{ error }}</p>
      <p v-else-if="tip" class="form-tip">{{ tip }}</p>

      <button class="login-btn" :disabled="loading">
        {{ loading ? '注册中…' : '注 册' }}
      </button>

      <p class="switch-link">
        已有账号？
        <a href="javascript:void(0)" @click="router.push('/login')">登录</a>
      </p>
    </form>
  </div>
</template>

<style scoped>
.login-page {
  width: min(100%, 430px);
  min-height: 100dvh;
  margin: 0 auto;
  padding: calc(128px + env(safe-area-inset-top, 0px)) 22px calc(28px + env(safe-area-inset-bottom, 0px));
  display: flex;
  flex-direction: column;
  align-items: center;
  background-color: #eaf3ff;
  background-size: cover;
  background-position: center top;
  background-repeat: no-repeat;
  box-sizing: border-box;
  position: relative;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-width: none;
}

.login-page::-webkit-scrollbar {
  display: none;
}

@media (min-width: 480px) {
  .login-page {
    min-height: min(100dvh - 48px, 920px);
    max-height: min(100dvh - 48px, 920px);
    border-radius: 28px;
    box-shadow:
      0 0 0 10px #1a2332,
      0 0 0 12px #334155,
      0 32px 64px rgba(0, 0, 0, 0.45);
  }
}

.login-brand {
  width: 100%;
  text-align: center;
  margin-bottom: clamp(64px, 14vh, 64px);
  animation: fade-up 0.45s ease both;
}

.login-logo {
  width: 78px;
  height: 78px;
  display: block;
  margin: 0 auto 16px;
  border-radius: 20px;
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.28);
  object-fit: cover;
}

.login-brand h1 {
  margin: 0;
  font-size: 34px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #1e3a8a;
  line-height: 1.2;
}

.brand-line {
  display: block;
  width: 36px;
  height: 3px;
  margin: 12px auto 10px;
  border-radius: 999px;
  background: linear-gradient(90deg, #60a5fa, #2563eb);
}

.login-brand p {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

.login-card {
  width: 100%;
  padding: 24px 20px 20px;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 22px;
  box-shadow: 0 16px 40px rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.auth-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin: -4px 0 16px;
  padding: 4px;
  border-radius: 14px;
  background: #f1f5fb;
}

.auth-tab {
  min-height: 38px;
  border: 0;
  border-radius: 11px;
  background: transparent;
  color: #64748b;
  font-size: 14px;
  font-weight: 700;
}

.auth-tab.is-active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.12);
}

.field {
  display: block;
  margin-bottom: 16px;
}

.field > span {
  display: block;
  margin-bottom: 7px;
  font-size: 13px;
  font-weight: 700;
  color: #334155;
}

.field-box {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
  padding: 0 14px;
  border-radius: 14px;
  background: #f5f8fc;
  border: 1.5px solid #e5edf7;
  transition: border-color 0.2s, box-shadow 0.2s, background 0.2s;
}

.field-box:focus-within {
  background: #fff;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.14);
}

.field-box .leading {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.field-box input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: none;
  background: transparent;
  padding: 12px 0;
  font-size: 15px;
  color: #1e293b;
}

.field-box input::placeholder {
  color: #b0b8c4;
}

.captcha-row,
.sms-row {
  padding-right: 8px;
}

.captcha-img {
  width: 110px;
  height: 38px;
  border: 0;
  border-radius: 10px;
  padding: 0;
  overflow: hidden;
  background: #e8eef8;
  flex-shrink: 0;
  cursor: pointer;
}

.captcha-img img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.captcha-img span {
  font-size: 12px;
  color: #64748b;
}

.sms-btn {
  border: 0;
  border-radius: 10px;
  background: #e8f1ff;
  color: #2563eb;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 12px;
  white-space: nowrap;
  flex-shrink: 0;
}

.sms-btn:disabled {
  opacity: 0.55;
  color: #64748b;
}

.hint {
  margin: 0 0 12px;
  font-size: 12px;
  line-height: 1.6;
  color: #94a3b8;
  text-align: center;
}

.form-error,
.form-tip {
  margin: 0 0 10px;
  font-size: 13px;
  text-align: center;
}

.form-error {
  color: #ef4444;
}

.form-tip {
  color: #2563eb;
}

.login-btn {
  width: 100%;
  min-height: 48px;
  margin-top: 4px;
  border: 0;
  border-radius: 999px;
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.12em;
  background: linear-gradient(180deg, #5ba0ff 0%, #2563eb 55%, #1d4ed8 100%);
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.35);
  position: relative;
  overflow: hidden;
}

.login-btn::before {
  content: "";
  position: absolute;
  inset: 0 0 50% 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.28), transparent);
  pointer-events: none;
}

.login-btn:disabled {
  opacity: 0.6;
}

.switch-link {
  margin: 16px 0 0;
  text-align: center;
  font-size: 13px;
  color: #64748b;
}

.switch-link a {
  color: #2563eb;
  font-weight: 700;
}
</style>
