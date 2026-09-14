import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useDialogStore = defineStore('dialog', () => {
  const visible = ref(false)
  const title = ref('提示')
  const message = ref('')
  const type = ref('warning')
  const mode = ref('alert')
  let resolver = null

  function open(payload) {
    message.value = payload.message || ''
    type.value = payload.type || 'warning'
    mode.value = payload.mode || 'alert'
    title.value = payload.title || (payload.mode === 'confirm' ? '请确认' : '提示')
    visible.value = true
    return new Promise((resolve) => {
      resolver = resolve
    })
  }

  function close(result = true) {
    visible.value = false
    resolver?.(result)
    resolver = null
  }

  function alert(text, kind = 'warning') {
    return open({ message: text, type: kind, mode: 'alert' })
  }

  function confirm(text) {
    return open({ message: text, type: 'warning', mode: 'confirm', title: '请确认' })
  }

  return { visible, title, message, type, mode, open, close, alert, confirm }
})
