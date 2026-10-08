// Owns microphone lifetime, including permission resolving after navigation.
export class AudioCapture {
  constructor({ onStop, onError, onLimit, platform = globalThis }) {
    Object.assign(this, { onStop, onError, onLimit, platform })
    this.disposed = false
    this.chunks = []
    this.bytes = 0
  }

  async start() {
    const { navigator, MediaRecorder, isSecureContext } = this.platform
    if (!isSecureContext || !navigator?.mediaDevices?.getUserMedia) {
      throw new Error('录音需要通过 HTTPS 或本机 localhost 打开页面；也可上传已有录音。')
    }
    if (!MediaRecorder) throw new Error('当前浏览器不支持页面录音，请更新浏览器或上传已有录音。')
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    if (this.disposed) { this.release(); return false }
    try {
      const mimeType = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/webm']
        .find((type) => MediaRecorder.isTypeSupported(type))
      this.recorder = new MediaRecorder(this.stream, mimeType ? { mimeType, audioBitsPerSecond: 64000 } : undefined)
      this.recorder.ondataavailable = ({ data }) => {
        if (data?.size) { this.chunks.push(data); this.bytes += data.size }
        if (this.bytes >= 70 * 1024 * 1024 && this.recorder.state === 'recording') {
          this.onLimit?.('录音已达到大小上限，已自动停止。')
          this.stop()
        }
      }
      this.recorder.onerror = () => {
        this.onError?.('录音意外中断，请检查麦克风后重试。')
        this.stop()
      }
      this.recorder.onstop = () => {
        this.release()
        if (this.disposed) return
        const type = this.recorder.mimeType || this.chunks[0]?.type || 'audio/webm'
        const extension = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm'
        const blob = new Blob(this.chunks, { type })
        this.chunks = []
        this.onStop(blob, extension)
      }
      this.recorder.start(1000)
      return true
    } catch (error) {
      this.release()
      throw error
    }
  }

  stop() {
    if (this.recorder && this.recorder.state !== 'inactive') this.recorder.stop()
    this.release()
  }

  release() {
    this.stream?.getTracks().forEach((track) => track.stop())
    this.stream = null
  }

  dispose() {
    this.disposed = true
    this.stop()
    this.chunks = []
  }
}
