<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useSmsCaptcha } from '../composables/useSmsCaptcha'
import { showAlert } from '../utils/dialog'
import logoImg from '../assets/icon/teach.webp'
import bgImg from '../assets/images/bg.webp'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const mode = ref(route.query.mode === 'sms' ? 'sms' : 'password')
const account = ref('')
const password = ref('')
const smsCode = ref('')
const showPassword = ref(false)
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

function switchMode(next) {
  mode.value = next
  error.value = ''
  tip.value = ''
}

async function sendCode() {
  error.value = ''
  tip.value = ''
  try {
    const data = await sendSmsCode(account.value.trim())
    tip.value = data.demo_code
      ? `验证码已发送（演示：${data.demo_code}）`
      : '验证码已发送，请注意查收'
  } catch (e) {
    error.value = e.message || '验证码发送失败'
  }
}

async function submit() {
  loading.value = true
  error.value = ''
  tip.value = ''
  try {
    if (mode.value === 'sms') {
      if (!/^1\d{10}$/.test(account.value.trim())) {
        error.value = '请输入正确的手机号'
        return
      }
      if (!smsCode.value.trim()) {
        error.value = '请输入短信验证码'
        return
      }
      const data = await auth.loginWithSms(account.value.trim(), smsCode.value.trim())
      if (data && data.existing === false) {
        await showAlert('注册成功。初始密码为 123456，请到「我的 → 设置」修改。')
      }
    } else {
      if (!account.value.trim() || !password.value) {
        error.value = '请输入手机号和密码'
        return
      }
      await auth.login(account.value.trim(), password.value)
    }
    router.replace('/')
  } catch (e) {
    const data = e.response?.data
    error.value = (typeof data?.detail === 'string' && data.detail)
      || data?.non_field_errors?.[0]
      || e.message
      || '登录失败，请确认账号密码或后端已启动'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-bg" :style="{ backgroundImage: `url(${bgImg})` }" aria-hidden="true" />
    <div class="login-inner">
      <header class="login-brand">
        <img class="login-logo" :src="logoImg" alt="教研云" width="72" height="72" fetchpriority="high" decoding="async" />
        <h1>教研云</h1>
        <i class="brand-line" aria-hidden="true" />
        <p>教师专业成长与协作教研平台</p>
      </header>

      <div class="login-gap" aria-hidden="true" />

      <form class="login-card" @submit.prevent="submit">
        <div class="auth-tabs" role="tablist">
          <button type="button" class="auth-tab" :class="{ 'is-active': mode === 'password' }" @click="switchMode('password')">密码登录</button>
          <button type="button" class="auth-tab" :class="{ 'is-active': mode === 'sms' }" @click="switchMode('sms')">验证码登录/注册</button>
        </div>

        <label class="field">
          <span>手机号</span>
          <div class="field-box">
            <svg class="leading" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="7" y="3" width="10" height="18" rx="2" stroke="#3b82f6" stroke-width="1.8" />
              <circle cx="12" cy="17" r="1" fill="#3b82f6" />
            </svg>
            <input
              v-model="account"
              inputmode="tel"
              autocomplete="tel"
              :maxlength="mode === 'sms' ? 11 : 20"
              :placeholder="mode === 'sms' ? '请输入手机号' : '请输入手机号或账号'"
            />
          </div>
        </label>

        <template v-if="mode === 'password'">
          <label class="field">
            <span>密码</span>
            <div class="field-box">
              <svg class="leading" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <rect x="5" y="11" width="14" height="10" rx="2" stroke="#3b82f6" stroke-width="1.8" />
                <path d="M8 11V8a4 4 0 0 1 8 0v3" stroke="#3b82f6" stroke-width="1.8" stroke-linecap="round" />
              </svg>
              <input
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="请输入密码"
              />
              <button
                type="button"
                class="eye-btn"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" stroke="#9aa3b2" stroke-width="1.7" />
                  <circle cx="12" cy="12" r="3" stroke="#9aa3b2" stroke-width="1.7" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path d="M3 3l18 18M10.6 10.6A3 3 0 0 0 12 15a3 3 0 0 0 2.4-4.8M9.9 5.1A11 11 0 0 1 12 5c6.5 0 10 7 10 7a18 18 0 0 1-4.2 4.8M6.1 6.1A18 18 0 0 0 2 12s3.5 7 10 7c1.1 0 2.1-.2 3.1-.5" stroke="#9aa3b2" stroke-width="1.7" stroke-linecap="round" />
                </svg>
              </button>
            </div>
          </label>
        </template>

        <template v-else>
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
        </template>

        <p v-if="error" class="form-error">{{ error }}</p>
        <p v-else-if="tip" class="form-tip">{{ tip }}</p>
        <p v-if="mode === 'password'" class="login-hint">初始密码为 123456。演示账号 teacher / teacher123 仍可登录。</p>
        <p v-else class="login-hint">未注册手机号将自动注册（初始密码 123456），已注册则直接登录。</p>

        <button class="login-btn" :disabled="loading">
          {{ loading ? '请稍候…' : (mode === 'sms' ? '登录 / 注册' : '登 录') }}
        </button>

        <p v-if="mode === 'password'" class="switch-link">
          还没有账号？
          <a href="javascript:void(0)" @click="switchMode('sms')">验证码登录/注册</a>
        </p>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  --login-pad-x: clamp(16px, 5.2vw, 22px);
  width: min(100%, 430px);
  height: 100vh;
  height: 100dvh;
  height: 100svh;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  background: #eaf3ff;
  box-sizing: border-box;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  background-color: #eaf3ff;
  background-size: cover;
  background-position: center top;
  background-repeat: no-repeat;
  pointer-events: none;
  z-index: 0;
}

.login-inner {
  position: relative;
  z-index: 1;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  overflow-x: hidden;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding:
    max(clamp(18px, 3.8vh, 36px), env(safe-area-inset-top, 0px))
    var(--login-pad-x)
    max(clamp(14px, 2.4vh, 24px), env(safe-area-inset-bottom, 0px));
  scrollbar-width: none;
}

.login-inner::-webkit-scrollbar {
  display: none;
}

@media (min-width: 480px) {
  .login-page {
    height: min(100dvh - 48px, 920px);
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
  flex-shrink: 0;
}

.login-logo {
  width: clamp(52px, 8.8vh, 72px);
  height: clamp(52px, 8.8vh, 72px);
  display: block;
  margin: 0 auto clamp(6px, 1vh, 12px);
  border-radius: 18px;
  box-shadow: 0 10px 22px rgba(37, 99, 235, 0.28);
  object-fit: cover;
}

.login-brand h1 {
  margin: 0;
  font-size: clamp(24px, 3.8vh, 30px);
  font-weight: 800;
  letter-spacing: 0.08em;
  color: #1e3a8a;
  line-height: 1.2;
}

.brand-line {
  display: block;
  width: 32px;
  height: 3px;
  margin: clamp(5px, 0.9vh, 9px) auto clamp(5px, 0.7vh, 8px);
  border-radius: 999px;
  background: linear-gradient(90deg, #60a5fa, #2563eb);
}

.login-brand p {
  margin: 0;
  font-size: clamp(12px, 1.6vh, 13px);
  color: #64748b;
  line-height: 1.5;
}

/* 品牌区与表单之间的弹性留白：高屏露出背景插画，矮屏自动收紧 */
.login-gap {
  width: 100%;
  flex: 1 1 auto;
  min-height: clamp(16px, 4.5vh, 36px);
  max-height: clamp(36px, 11vh, 108px);
  pointer-events: none;
}

.login-card {
  width: 100%;
  padding: clamp(14px, 2.2vh, 20px) clamp(14px, 4vw, 20px) clamp(12px, 1.8vh, 18px);
  background: rgba(255, 255, 255, 0.96);
  border-radius: 22px;
  box-shadow: 0 16px 40px rgba(37, 99, 235, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
  flex-shrink: 0;
}

.auth-tabs {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.2fr);
  gap: 6px;
  margin: 0 0 14px;
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
  font-size: 13px;
  font-weight: 700;
  padding: 0 6px;
  white-space: nowrap;
}

.auth-tab.is-active {
  background: #fff;
  color: #2563eb;
  box-shadow: 0 4px 10px rgba(37, 99, 235, 0.12);
}

.field {
  display: block;
  margin-bottom: clamp(10px, 1.8vh, 16px);
}

.field > span {
  display: block;
  margin-bottom: 6px;
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
  font-size: 16px;
  color: #1e293b;
}

.field-box input::placeholder {
  color: #b0b8c4;
}

.eye-btn {
  width: 32px;
  height: 32px;
  border: 0;
  padding: 0;
  background: transparent;
  display: grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 8px;
}

.eye-btn svg {
  width: 20px;
  height: 20px;
}

.form-error,
.form-tip {
  margin: 0 0 12px;
  font-size: 13px;
  text-align: center;
}

.form-error {
  color: #ef4444;
}

.form-tip {
  color: #2563eb;
}

.captcha-row,
.sms-row {
  padding-right: 8px;
}

.captcha-img {
  width: min(138px, 38vw);
  height: 46px;
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
  object-fit: contain;
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

.login-hint {
  margin: 0 0 10px;
  font-size: 12px;
  color: #8a93a3;
  text-align: center;
  line-height: 1.45;
}

.login-btn {
  width: 100%;
  min-height: 48px;
  margin-top: 4px;
  border: 0;
  border-radius: 999px;
  color: #fff;
  font-size: 17px;
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

.login-btn:active:not(:disabled) {
  transform: scale(0.985);
}

.login-btn:disabled {
  opacity: 0.6;
}

.switch-link {
  margin: 12px 0 0;
  text-align: center;
  font-size: 13px;
  color: #64748b;
}

.switch-link a {
  color: #2563eb;
  font-weight: 700;
}

@media (max-height: 700px) {
  .login-gap {
    flex: 0 0 auto;
    min-height: 10px;
    max-height: 18px;
  }

  .login-logo {
    width: 52px;
    height: 52px;
    border-radius: 15px;
  }

  .field-box {
    min-height: 44px;
  }

  .login-btn {
    min-height: 44px;
  }
}

@media (max-width: 360px) {
  .auth-tab {
    font-size: 12px;
    padding: 0 4px;
  }

  .captcha-img {
    width: 112px;
    height: 40px;
  }

  .sms-btn {
    padding: 8px 8px;
    font-size: 12px;
  }
}
</style>
