/**
 * Imperative confirm/alert API for VgDialog (promise-based).
 */
import { reactive } from 'vue'

export const dialogState = reactive({
  open: false,
  mode: 'confirm', // confirm | alert
  title: '',
  message: '',
  confirmText: '确定',
  cancelText: '取消',
  tone: 'default', // default | danger | primary
  /** @type {null | ((v: boolean) => void)} */
  _resolve: null,
})

function openDialog(options) {
  return new Promise((resolve) => {
    // Close any existing dialog as cancel
    if (dialogState.open && dialogState._resolve) {
      dialogState._resolve(false)
    }
    dialogState.mode = options.mode || 'confirm'
    dialogState.title = options.title || (options.mode === 'alert' ? '提示' : '请确认')
    dialogState.message = options.message || ''
    dialogState.confirmText = options.confirmText || '确定'
    dialogState.cancelText = options.cancelText || '取消'
    dialogState.tone = options.tone || 'default'
    dialogState.open = true
    dialogState._resolve = resolve
  })
}

export function closeDialog(result) {
  const resolve = dialogState._resolve
  dialogState.open = false
  dialogState._resolve = null
  if (resolve) resolve(Boolean(result))
}

/** Confirm dialog — resolves true/false */
export function vgConfirm(message, options = {}) {
  if (typeof message === 'object' && message !== null) {
    return openDialog({ mode: 'confirm', ...message })
  }
  return openDialog({
    mode: 'confirm',
    message: String(message || ''),
    title: options.title,
    confirmText: options.confirmText,
    cancelText: options.cancelText,
    tone: options.tone || 'danger',
  })
}

/** Alert dialog — single button, resolves true when closed */
export function vgAlert(message, options = {}) {
  if (typeof message === 'object' && message !== null) {
    return openDialog({ mode: 'alert', tone: 'primary', ...message })
  }
  return openDialog({
    mode: 'alert',
    message: String(message || ''),
    title: options.title || '提示',
    confirmText: options.confirmText || '知道了',
    tone: options.tone || 'primary',
  })
}
