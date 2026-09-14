<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { lessonApi, reportsApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import MarkdownBlock from '../components/MarkdownBlock.vue'
import { takeAiJob } from '../utils/aiJob'
import { postSse } from '../utils/sse'
import { downloadBlob } from '../utils/download'
import { errorMessage, showAlert } from '../utils/dialog'
import { useNoticeStore } from '../stores/notices'

const route = useRoute()
const router = useRouter()
const kind = ref(route.meta.kind || 'report')
const isLesson = () => kind.value === 'lesson'

const status = ref('idle')
const title = ref('')
const content = ref('')
const savedId = ref(null)
const downloading = ref(false)
const errorText = ref('')
const bottomEl = ref(null)
const abort = new AbortController()

const pageTitle = () => (isLesson() ? '个人教学设计' : '研修总结报告')
const historyTo = () => (isLesson() ? '/lesson-plans' : '/reports')
const formTo = () => (isLesson() ? '/lesson-design' : '/reports/generate')

async function scrollToBottom() {
  await nextTick()
  bottomEl.value?.scrollIntoView({ block: 'end' })
}

async function downloadWord() {
  if (!savedId.value) return
  downloading.value = true
  try {
    const res = isLesson()
      ? await lessonApi.exportPlan(savedId.value)
      : await reportsApi.exportDocx(savedId.value)
    await downloadBlob(res, `${title.value || pageTitle()}.docx`)
  } catch (e) {
    showAlert(errorMessage(e, '导出失败'), 'error')
  } finally {
    downloading.value = false
  }
}

onMounted(async () => {
  const job = takeAiJob()
  if (!job?.payload) {
    router.replace(formTo())
    return
  }
  kind.value = job.kind || kind.value
  title.value = job.title || pageTitle()
  status.value = 'streaming'
  try {
    await postSse(
      isLesson() ? '/api/lesson-plans/generate-stream/' : '/api/reports/generate-stream/',
      job.payload,
      {
        signal: abort.signal,
        onEvent(event) {
          if (event.delta) {
            content.value += event.delta
            scrollToBottom()
          }
          if (event.error) {
            errorText.value = event.error
            status.value = 'error'
          }
          if (event.done) {
            savedId.value = event.id
            if (event.title) title.value = event.title
            status.value = 'done'
            useNoticeStore().refresh()
          }
        },
      },
    )
    if (status.value === 'streaming') {
      status.value = content.value ? 'done' : 'error'
      if (!content.value) errorText.value = '未收到生成内容，请重试'
    }
  } catch (e) {
    if (e.name === 'AbortError') return
    errorText.value = errorMessage(e, '生成失败')
    status.value = 'error'
  }
})

onUnmounted(() => abort.abort())
</script>

<template>
  <main class="sub-page output-page">
    <PageHeader :title="pageTitle()" back />
    <div class="page-body">
      <section class="stream-status" :class="[kind, status]">
        <div>
          <b>{{ title || pageTitle() }}</b>
          <small v-if="status === 'streaming'">AI 正在撰写，请稍候…</small>
          <small v-else-if="status === 'done'">已完成，可下载 Word、编辑内容，或稍后在历史中查看</small>
          <small v-else-if="status === 'error'">生成中断，可返回修改后重试</small>
          <small v-else>准备开始</small>
        </div>
        <em v-if="status === 'streaming'">撰写中</em>
        <em v-else-if="status === 'done'">已完成</em>
        <em v-else-if="status === 'error'">失败</em>
      </section>

      <section class="result-card stream-card">
        <p v-if="!content && status === 'streaming'" class="stream-placeholder">正在组织内容…</p>
        <MarkdownBlock v-if="content" :content="content" />
        <span v-if="status === 'streaming'" class="stream-cursor" />
        <p v-if="errorText" class="stream-error">{{ errorText }}</p>
        <div ref="bottomEl" />
      </section>

      <div class="output-actions">
        <button
          type="button"
          class="primary-button"
          :class="{ 'orange-button': isLesson() }"
          :disabled="status !== 'done' || downloading"
          @click="downloadWord"
        >
          {{ downloading ? '正在导出…' : '下载 Word' }}
        </button>
        <button type="button" class="secondary-button" :disabled="status !== 'done'" @click="router.push(`${historyTo()}/${savedId}`)">
          查看并编辑
        </button>
        <button type="button" class="secondary-button" @click="router.push(historyTo())">查看历史</button>
        <button v-if="status === 'error'" type="button" class="secondary-button" @click="router.replace(formTo())">
          返回修改
        </button>
      </div>
    </div>
  </main>
</template>

<style scoped>
.stream-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  margin-bottom: 14px;
  border-radius: 16px;
  background: #fff;
  border: 1px solid var(--line);
}
.stream-status.lesson {
  background: linear-gradient(180deg, #fff8f3, #fff);
}
.stream-status div {
  flex: 1;
  min-width: 0;
}
.stream-status b {
  display: block;
  font-size: 15px;
}
.stream-status small {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}
.stream-status em {
  flex-shrink: 0;
  font-style: normal;
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 5px 10px;
  background: var(--blue);
  color: #fff;
}
.stream-status.streaming em {
  background: var(--blue);
}
.stream-status.done em {
  background: var(--success);
}
.stream-status.error em {
  background: var(--danger);
}
.stream-card {
  min-height: 280px;
}
.stream-placeholder,
.stream-error {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
}
.stream-error {
  margin-top: 12px;
  color: var(--danger);
}
.stream-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  background: var(--blue);
  animation: blink 0.9s step-end infinite;
  vertical-align: text-bottom;
}
.output-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 12px;
}
.output-actions .secondary-button {
  width: 100%;
  min-height: 44px;
}
@keyframes blink {
  50% { opacity: 0; }
}
</style>
