import { useDialogStore } from '../stores/dialog'

export function showAlert(message, type = 'warning') {
  return useDialogStore().alert(message, type)
}

export function showConfirm(message) {
  return useDialogStore().confirm(message)
}

export function errorMessage(error, fallback = '操作失败') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (typeof error?.message === 'string' && error.message && error.message !== 'Error') return error.message
  return fallback
}
