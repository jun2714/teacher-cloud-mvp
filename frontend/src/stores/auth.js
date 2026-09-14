import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)
  const isLoggedIn = computed(() => Boolean(localStorage.getItem('access_token')))

  function applyAuth(data) {
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    if (data.user) user.value = data.user
  }

  async function login(username, password) {
    const { data } = await authApi.login({ username, password })
    applyAuth(data)
    await fetchMe()
  }

  async function loginWithSms(phone, smsCode) {
    const { data } = await authApi.smsLogin({ phone, sms_code: smsCode })
    applyAuth(data)
    await fetchMe()
    return data
  }

  async function register(payload) {
    const { data } = await authApi.register(payload)
    applyAuth(data)
    await fetchMe()
    return data
  }

  async function fetchMe() {
    if (!isLoggedIn.value) return
    loading.value = true
    try {
      const { data } = await authApi.me()
      user.value = data
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(payload) {
    const { data } = await authApi.updateMe(payload)
    user.value = data
    return data
  }

  async function logout() {
    const refresh = localStorage.getItem('refresh_token')
    try {
      if (refresh) await authApi.logout(refresh)
    } catch {
      /* 本地仍清登录态 */
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    user.value = null
  }

  return { user, loading, isLoggedIn, login, loginWithSms, register, fetchMe, updateProfile, logout }
})
