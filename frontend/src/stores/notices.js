import { defineStore } from 'pinia'
import { ref } from 'vue'
import { noticeApi } from '../api'

export const useNoticeStore = defineStore('notices', () => {
  const unread = ref(0)
  const toast = ref(null)
  let known = null
  let timer = null

  async function refresh({ silent = false } = {}) {
    if (!localStorage.getItem('access_token')) {
      unread.value = 0
      return
    }
    try {
      const data = await noticeApi.unread()
      const next = data.count || 0
      if (!silent && known != null && next > known && data.latest) {
        toast.value = data.latest
      }
      known = next
      unread.value = next
    } catch {
      /* ignore polling errors */
    }
  }

  function start() {
    stop()
    refresh({ silent: true })
    timer = setInterval(() => refresh(), 20000)
  }

  function stop() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function clearToast() {
    toast.value = null
  }

  async function markAllRead() {
    await noticeApi.markRead()
    unread.value = 0
    known = 0
  }

  return { unread, toast, refresh, start, stop, clearToast, markAllRead }
})
