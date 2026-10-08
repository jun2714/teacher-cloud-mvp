import test from 'node:test'
import assert from 'node:assert/strict'
import { AudioCapture } from '../src/utils/audioRecorder.js'
import { appendMaterial, classifyMaterial } from '../src/utils/reviewMaterials.js'

function platform(options = {}) {
  let released = 0
  const stream = { getTracks: () => [{ stop: () => released++ }] }
  class Recorder {
    static isTypeSupported = (type) => type === 'audio/mp4'
    constructor(stream, options) { this.mimeType = options.mimeType; this.state = 'inactive' }
    start() { this.state = 'recording' }
    stop() {
      this.state = 'inactive'
      this.ondataavailable({ data: new Blob(['a'.repeat(500)], { type: this.mimeType }) })
      this.onstop()
    }
  }
  return { value: { isSecureContext: true, MediaRecorder: Recorder, navigator: { mediaDevices: { getUserMedia: options.getUserMedia || (async () => stream) } } }, stream, released: () => released }
}

test('stop includes final data, chooses supported format, and releases microphone', async () => {
  const env = platform()
  let result
  const capture = new AudioCapture({ platform: env.value, onStop: (...args) => { result = args } })
  await capture.start()
  capture.stop()
  assert.equal(result[0].size, 500)
  assert.equal(result[1], 'm4a')
  assert.equal(env.released(), 1)
})

test('leaving before microphone permission resolves releases late stream', async () => {
  let resolve
  const env = platform({ getUserMedia: () => new Promise((done) => { resolve = done }) })
  const capture = new AudioCapture({ platform: env.value, onStop: () => assert.fail('must not upload after leaving') })
  const pending = capture.start()
  capture.dispose()
  resolve(env.stream)
  assert.equal(await pending, false)
  assert.equal(env.released(), 1)
})

test('dispose suppresses recording upload on navigation', async () => {
  const env = platform()
  const capture = new AudioCapture({ platform: env.value, onStop: () => assert.fail('unexpected upload') })
  await capture.start()
  capture.dispose()
  assert.equal(env.released(), 1)
})

test('insecure context and permission denial fail explicitly', async () => {
  const env = platform()
  env.value.isSecureContext = false
  await assert.rejects(new AudioCapture({ platform: env.value }).start(), /HTTPS/)
  const denied = platform({ getUserMedia: async () => { throw new Error('denied') } })
  await assert.rejects(new AudioCapture({ platform: denied.value }).start(), /denied/)
})

test('material append preserves edits and refuses oversized or blank results', () => {
  assert.match(appendMaterial('老师手动修订', '教案.docx', '第二份材料'), /^老师手动修订\n\n/)
  assert.throws(() => appendMaterial('原文', '空.pdf', ' '), /未识别/)
  assert.throws(() => appendMaterial('字'.repeat(60000), '教案', '多出的内容'), /60000/)
  assert.equal(classifyMaterial({ name: 'PHOTO.JPG', size: 100 }), 'document')
  assert.equal(classifyMaterial({ name: '录音.webm', size: 100 }), 'media')
  assert.throws(() => classifyMaterial({ name: '教案.doc', size: 100 }), /另存为/)
})
