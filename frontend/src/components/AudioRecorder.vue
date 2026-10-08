<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { AudioCapture } from '../utils/audioRecorder'

const props = defineProps({ disabled: Boolean })
const emit = defineEmits(['recorded', 'busy'])
const state = ref('idle')
const seconds = ref(0)
const error = ref('')
const notice = ref('')
const audioUrl = ref('')
const filename = ref('')
const elapsed = computed(() => `${Math.floor(seconds.value / 60).toString().padStart(2, '0')}:${(seconds.value % 60).toString().padStart(2, '0')}`)
let capture, timer, startedAt

function finish() {
  clearInterval(timer)
  state.value = 'idle'
  emit('busy', false)
}

function stop() {
  state.value = 'stopping'
  clearInterval(timer)
  capture?.stop()
}

async function start() {
  if (props.disabled || state.value !== 'idle') return
  error.value = ''
  notice.value = ''
  state.value = 'requesting'
  emit('busy', true)
  capture?.dispose()
  capture = new AudioCapture({
    onError: (message) => { error.value = message },
    onLimit: (message) => { notice.value = message },
    onStop: (blob, extension) => {
      finish()
      if (blob.size < 200) { error.value = '录音过短，请重新录制。'; return }
      if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
      audioUrl.value = URL.createObjectURL(blob)
      filename.value = `课堂录音-${Date.now()}.${extension}`
      emit('recorded', new File([blob], filename.value, { type: blob.type }))
    },
  })
  try {
    if (!await capture.start()) return
    state.value = 'recording'
    seconds.value = 0
    startedAt = Date.now()
    timer = setInterval(() => {
      seconds.value = Math.floor((Date.now() - startedAt) / 1000)
      if (seconds.value >= 3600) {
        notice.value = '已录制 60 分钟，自动停止并转写。需要时可继续录制下一段。'
        stop()
      }
    }, 1000)
  } catch (err) {
    finish()
    error.value = ({
      NotAllowedError: '未获得麦克风权限，请在浏览器地址栏允许麦克风后重试。',
      NotFoundError: '没有找到麦克风，请连接麦克风或上传已有录音。',
      NotReadableError: '麦克风被占用或无法读取，请关闭其他录音应用后重试。',
    })[err.name] || err.message || '无法开始录音，请重试。'
  }
}

onBeforeUnmount(() => {
  clearInterval(timer)
  capture?.dispose()
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value)
})
</script>

<template>
  <section class="recorder" aria-label="直接录音">
    <div class="recorder-heading">
      <b>直接录音</b>
      <span v-if="state === 'recording'" class="recording-time" role="timer">录音中 {{ elapsed }}</span>
    </div>
    <p>点击开始，停止后自动转为文字。每段最长 60 分钟，录音时请保持页面打开。</p>
    <div class="recorder-actions">
      <button v-if="state === 'recording'" type="button" class="danger-button" @click="stop">停止并转写</button>
      <button v-else type="button" class="secondary-button" :disabled="disabled || state !== 'idle'" @click="start">
        {{ state === 'requesting' ? '等待麦克风授权…' : state === 'stopping' ? '正在保存录音…' : audioUrl ? '录制下一段' : '开始录音' }}
      </button>
      <a v-if="audioUrl" :href="audioUrl" :download="filename">下载这段录音</a>
    </div>
    <p v-if="notice" role="status">{{ notice }}</p>
    <p v-if="error" class="recorder-error" role="alert">{{ error }}</p>
    <audio v-if="audioUrl" :src="audioUrl" controls aria-label="回听刚才的录音" />
  </section>
</template>

<style scoped>
.recorder { padding: 16px; margin-bottom: 16px; border: 1px solid #d6e6ff; border-radius: 12px; background: #f6f9ff; }
.recorder-heading, .recorder-actions { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.recorder p { margin: 8px 0 12px; font-size: 13px; line-height: 1.6; color: #53647c; }
.recorder-actions button, .recorder-actions a { min-height: 44px; }
.recorder-actions a { display: inline-flex; align-items: center; font-size: 13px; color: var(--blue); }
.recording-time, .recorder .recorder-error { color: #b42318; }
.recording-time { font-variant-numeric: tabular-nums; }
.recorder audio { width: 100%; margin-top: 12px; }
</style>
