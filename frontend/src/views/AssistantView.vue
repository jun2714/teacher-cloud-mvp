<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { assistantApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import MarkdownBlock from '../components/MarkdownBlock.vue'
import { postSse } from '../utils/sse'
import { errorMessage, showAlert, showConfirm } from '../utils/dialog'
import iconNew from '../assets/images/icon-chat-new.png'
import iconHistory from '../assets/images/icon-chat-history.png'
import iconUpload from '../assets/images/icon-chat-upload.png'

const ALLOWED_EXT = ['.txt', '.md', '.docx', '.pdf', '.csv', '.json', '.png', '.jpg', '.jpeg', '.webp', '.gif']
const MAX_FILE_SIZE = 8 * 1024 * 1024

const chats = ref([])
const chatId = ref(null)
const messages = ref([])
const input = ref('')
const pendingFile = ref(null)
const fileInput = ref(null)
const sending = ref(false)
const loading = ref(true)
const showHistory = ref(false)
const listEl = ref(null)
const abort = ref(null)

function displayUserText(msg) {
  const raw = msg.content || ''
  const idx = raw.indexOf('\n\n【上传文件：')
  return idx >= 0 ? raw.slice(0, idx) : raw
}

async function refreshList() {
  chats.value = await assistantApi.list()
}

async function openChat(id) {
  const data = await assistantApi.detail(id)
  chatId.value = data.id
  messages.value = data.messages || []
  showHistory.value = false
  await scrollBottom()
}

function newChat() {
  chatId.value = null
  messages.value = []
  showHistory.value = false
}

async function scrollBottom() {
  await nextTick()
  listEl.value?.scrollTo({ top: listEl.value.scrollHeight, behavior: 'smooth' })
}

function pickFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  const ext = `.${(file.name.split('.').pop() || '').toLowerCase()}`
  if (!ALLOWED_EXT.includes(ext)) {
    showAlert('请上传 txt、md、docx、pdf、csv、json 或图片文件')
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    showAlert('文件不能超过 8MB')
    return
  }
  pendingFile.value = file
}

async function send() {
  const text = input.value.trim()
  const file = pendingFile.value
  if ((!text && !file) || sending.value) return
  input.value = ''
  pendingFile.value = null
  messages.value.push({
    role: 'user',
    content: text || `请分析我上传的文件「${file.name}」。`,
    attachment_name: file?.name || '',
  })
  messages.value.push({ role: 'assistant', content: '' })
  const reply = messages.value[messages.value.length - 1]
  sending.value = true
  abort.value = new AbortController()
  await scrollBottom()
  try {
    const body = new FormData()
    if (chatId.value) body.append('chat_id', String(chatId.value))
    body.append('content', text)
    if (file) body.append('file', file)
    await postSse('/api/assistant-chats/send-stream/', body, {
      signal: abort.value.signal,
      onEvent(event) {
        if (event.chat_id) chatId.value = event.chat_id
        if (event.delta) {
          reply.content += event.delta
          scrollBottom()
        }
        if (event.error) {
          reply.content = event.error
        }
      },
    })
    if (!reply.content) reply.content = '暂时没有生成回答，请再试一次。'
    await refreshList()
  } catch (e) {
    if (e.name === 'AbortError') return
    reply.content = errorMessage(e, '发送失败，请稍后重试')
    showAlert(reply.content, 'error')
  } finally {
    sending.value = false
    abort.value = null
  }
}

async function removeChat(item) {
  const ok = await showConfirm(`删除对话「${item.title}」？`)
  if (!ok) return
  await assistantApi.remove(item.id)
  if (chatId.value === item.id) newChat()
  await refreshList()
}

onMounted(async () => {
  try {
    await refreshList()
  } finally {
    loading.value = false
  }
})

onUnmounted(() => abort.value?.abort())
</script>

<template>
  <main class="sub-page chat-page">
    <PageHeader title="教研云智能助手" back />
    <div class="chat-toolbar">
      <button type="button" class="toolbar-btn" @click="newChat">
        <img :src="iconNew" alt="" />
        新对话
      </button>
      <button type="button" class="toolbar-btn" :class="{ active: showHistory }" @click="showHistory = !showHistory">
        <img :src="iconHistory" alt="" />
        历史
      </button>
    </div>
    <div v-if="showHistory" class="chat-history">
      <article v-if="!chats.length" class="empty-card">还没有历史对话</article>
      <article v-for="item in chats" :key="item.id" class="mini-report is-link" role="button" @click="openChat(item.id)">
        <span>✦</span>
        <div>
          <b>{{ item.title }}</b>
          <small>{{ new Date(item.updated_at).toLocaleString() }}</small>
        </div>
        <button type="button" class="history-del" @click.stop="removeChat(item)">删</button>
      </article>
    </div>
    <div ref="listEl" class="chat-list">
      <div v-if="loading" class="loading-card">加载中…</div>
      <section v-else-if="!messages.length" class="chat-welcome">
        <h2>你好，我是教研云智能助手</h2>
        <p>可以问备课思路、课堂任务设计、评课观察要点，也可以上传教案、学案或文本材料进行分析。回答仅供教研参考。</p>
      </section>
      <article v-for="(msg, index) in messages" :key="index" class="bubble" :class="msg.role">
        <b>{{ msg.role === 'user' ? '我' : '助手' }}</b>
        <MarkdownBlock v-if="msg.role === 'assistant'" :content="msg.content || (sending ? '正在思考…' : '')" />
        <template v-else>
          <p>{{ displayUserText(msg) }}</p>
          <a v-if="msg.attachment_url" class="file-tag" :href="msg.attachment_url" target="_blank" rel="noreferrer">附件：{{ msg.attachment_name }}</a>
          <span v-else-if="msg.attachment_name" class="file-tag">附件：{{ msg.attachment_name }}</span>
        </template>
      </article>
    </div>
    <form class="chat-input" @submit.prevent="send">
      <input
        ref="fileInput"
        class="file-hidden"
        type="file"
        accept=".txt,.md,.docx,.pdf,.csv,.json,image/*"
        :disabled="sending"
        @change="pickFile"
      />
      <button type="button" class="upload-btn" :disabled="sending" title="上传文件分析" @click="fileInput?.click()">
        <img :src="iconUpload" alt="上传" />
      </button>
      <div class="input-wrap">
        <div v-if="pendingFile" class="file-chip">
          <span>{{ pendingFile.name }}</span>
          <button type="button" :disabled="sending" @click="pendingFile = null">×</button>
        </div>
        <input v-model="input" maxlength="2000" :disabled="sending" placeholder="输入问题，或上传文件后发送" />
      </div>
      <button type="submit" :disabled="sending || (!input.trim() && !pendingFile)">{{ sending ? '…' : '发送' }}</button>
    </form>
  </main>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}
.chat-toolbar {
  display: flex;
  gap: 8px;
  padding: 8px 14px 0;
}
.toolbar-btn,
.history-del {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  border-radius: 999px;
  background: #e8f1ff;
  color: var(--blue);
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 700;
}
.toolbar-btn img {
  width: 16px;
  height: 16px;
  object-fit: contain;
}
.toolbar-btn.active {
  background: var(--blue);
  color: #fff;
}
.chat-history {
  padding: 10px 14px 0;
  max-height: 180px;
  overflow: auto;
}
.history-del {
  flex-shrink: 0;
  background: #fff1f0;
  color: #f04438;
}
.chat-list {
  flex: 1;
  overflow: auto;
  padding: 12px 14px 12px;
}
.chat-welcome {
  padding: 28px 12px;
  text-align: center;
}
.chat-welcome h2 {
  margin: 0;
  font-size: 17px;
}
.chat-welcome p {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.6;
}
.bubble {
  max-width: 92%;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid var(--line);
}
.bubble.user {
  margin-left: auto;
  background: #e8f1ff;
  border-color: #d6e6ff;
}
.bubble b {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--muted);
}
.bubble p {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.file-tag {
  display: inline-block;
  margin-top: 8px;
  padding: 4px 8px;
  border-radius: 8px;
  background: #fff;
  color: var(--blue);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 14px calc(12px + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid var(--line);
}
.file-hidden {
  display: none;
}
.upload-btn {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #f8fafc;
  padding: 0;
}
.upload-btn img {
  width: 22px;
  height: 22px;
  object-fit: contain;
}
.upload-btn:disabled {
  opacity: 0.5;
}
.input-wrap {
  flex: 1;
  min-width: 0;
}
.file-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  padding: 4px 8px;
  border-radius: 8px;
  background: #e8f1ff;
  color: var(--blue);
  font-size: 12px;
  font-weight: 700;
}
.file-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-chip button {
  border: 0;
  background: transparent;
  color: var(--muted);
  padding: 0 2px;
  font-size: 16px;
  line-height: 1;
}
.chat-input .input-wrap input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  background: #f8fafc;
}
.chat-input > button[type='submit'] {
  flex-shrink: 0;
  height: 42px;
  border: 0;
  border-radius: 12px;
  background: var(--blue);
  color: #fff;
  padding: 0 14px;
  font-weight: 700;
}
.chat-input > button[type='submit']:disabled {
  opacity: 0.5;
}
</style>
