import { onMounted, onUnmounted, ref } from 'vue'
import { authApi } from '../api'

export function useSmsCaptcha() {
  const captchaId = ref('')
  const captchaImage = ref('')
  const captchaCode = ref('')
  const sending = ref(false)
  const cooldown = ref(0)
  let timer = null

  async function loadCaptcha({ clearInput = true } = {}) {
    const { data } = await authApi.captcha()
    captchaId.value = data.captcha_id
    captchaImage.value = data.image
    if (clearInput) captchaCode.value = ''
  }

  function startCooldown(seconds = 60) {
    cooldown.value = seconds
    clearInterval(timer)
    timer = setInterval(() => {
      cooldown.value -= 1
      if (cooldown.value <= 0) {
        clearInterval(timer)
        timer = null
      }
    }, 1000)
  }

  async function sendSmsCode(phone) {
    if (!/^1\d{10}$/.test(phone || '')) {
      throw new Error('请输入正确的手机号')
    }
    if (!captchaCode.value.trim()) {
      throw new Error('请输入图形验证码')
    }
    sending.value = true
    try {
      const { data } = await authApi.sendSmsCode({
        phone,
        captcha_id: captchaId.value,
        captcha_code: captchaCode.value,
      })
      startCooldown(data.cooldown || 60)
      return data
    } catch (e) {
      const detail = e.response?.data?.detail || e.message || '验证码发送失败'
      if (!String(detail).includes('图形验证码')) {
        try {
          await loadCaptcha()
        } catch {
          /* 保留已填图形码，避免发送失败后输入被清空 */
        }
      }
      throw new Error(detail)
    } finally {
      sending.value = false
    }
  }

  onMounted(() => {
    loadCaptcha().catch(() => {})
  })
  onUnmounted(() => clearInterval(timer))

  return {
    captchaId,
    captchaImage,
    captchaCode,
    sending,
    cooldown,
    loadCaptcha,
    sendSmsCode,
  }
}
