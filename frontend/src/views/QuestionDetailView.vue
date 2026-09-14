<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { communityApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import MarkdownBlock from '../components/MarkdownBlock.vue'
import { showConfirm } from '../utils/dialog'

const route = useRoute()
const question = ref(null)
const answerText = ref('')
const submitting = ref(false)

function formatTime(value) {
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function avatarText(info) {
  return info?.profile?.avatar_text || info?.display_name?.[0] || '师'
}

async function load() {
  question.value = (await communityApi.detail(route.params.id)).data
}

async function submit() {
  if (!answerText.value.trim()) return
  submitting.value = true
  try {
    await communityApi.answer(question.value.id, answerText.value)
    answerText.value = ''
    await load()
  } finally {
    submitting.value = false
  }
}

async function likeAnswer(a) {
  const { data } = await communityApi.toggleAnswerLike(a.id)
  a.is_liked = data.liked
  a.like_count = data.like_count
}

async function solve(a) {
  if (!(await showConfirm('确认将这条回答采纳并标记为已解答吗？'))) return
  question.value = (await communityApi.markSolved(question.value.id, a.id)).data
}

onMounted(load)
</script>

<template>
  <main class="sub-page">
    <PageHeader title="问题详情" back />
    <div v-if="question" class="page-body">
      <article class="topic-card">
        <div class="topic-meta">
          <span class="avatar">
            <img v-if="question.author_info.profile?.avatar_url" :src="question.author_info.profile.avatar_url" alt="" />
            <template v-else>{{ avatarText(question.author_info) }}</template>
          </span>
          <div>
            <b>{{ question.author_info.display_name }}</b>
            <time>{{ formatTime(question.created_at) }} 提问</time>
          </div>
          <em :class="question.status">{{ question.status_label }}</em>
        </div>
        <h2>{{ question.title }}</h2>
        <p class="topic-body">{{ question.content }}</p>
        <div class="tag-list">
          <span v-for="tag in question.tags" :key="tag">{{ tag }}</span>
        </div>
        <p v-if="question.ai_failed" class="ai-fail-banner">AI 参考回答暂时无法生成，可稍后重试发布，或直接邀请同事作答。</p>
      </article>

      <div class="reply-section">
        <h3 class="reply-label">
          回答
          <span>{{ question.answers.length }}</span>
        </h3>

        <article v-if="!question.answers.length" class="empty-card">还没有人回答，欢迎分享你的做法</article>

        <article
          v-for="a in question.answers"
          :key="a.id"
          class="reply"
          :class="{ ai: a.answer_type === 'ai', accepted: a.is_accepted }"
        >
          <div class="reply-meta">
            <span class="avatar sm" :class="{ bot: a.answer_type === 'ai' }">
              <img
                v-if="a.answer_type !== 'ai' && a.author_info?.profile?.avatar_url"
                :src="a.author_info.profile.avatar_url"
                alt=""
              />
              <template v-else>{{ a.answer_type === 'ai' ? 'AI' : avatarText(a.author_info) }}</template>
            </span>
            <b>{{ a.answer_type === 'ai' ? '教研云助手' : a.author_info?.display_name }}</b>
            <em class="kind" :class="a.answer_type">{{ a.answer_type === 'ai' ? '参考回答' : '教师回答' }}</em>
            <time>{{ formatTime(a.created_at) }}</time>
            <i v-if="a.is_accepted">已采纳</i>
          </div>

          <div class="reply-body">
            <p v-if="a.answer_type === 'ai'" class="ai-hint">根据提问生成，供备课参考，不能替代同事讨论。</p>
            <MarkdownBlock :content="a.content" />
          </div>

          <footer class="reply-foot">
            <button type="button" :class="{ liked: a.is_liked }" @click="likeAnswer(a)">
              {{ a.is_liked ? '♥' : '♡' }} {{ a.like_count }} 有帮助
            </button>
            <button
              v-if="question.is_owner && question.status !== 'solved'"
              type="button"
              class="accept-button"
              @click="solve(a)"
            >采纳这条</button>
          </footer>
        </article>
      </div>

      <section class="answer-editor">
        <label>写回答</label>
        <textarea v-model="answerText" rows="4" placeholder="补充课堂做法、注意事项或不同意见…" />
        <button class="primary-button" type="button" :disabled="submitting" @click="submit">
          {{ submitting ? '提交中…' : '提交回答' }}
        </button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.topic-card {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(26, 45, 90, 0.03);
}

.topic-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.topic-meta > div {
  flex: 1;
  min-width: 0;
}

.topic-meta b,
.topic-meta time {
  display: block;
}

.topic-meta b {
  font-size: 14px;
}

.topic-meta time {
  margin-top: 2px;
  font-size: 11px;
  color: var(--muted);
}

.topic-meta em {
  font-size: 11px;
  font-style: normal;
  border-radius: 999px;
  padding: 4px 9px;
  font-weight: 600;
  flex-shrink: 0;
}

.topic-meta em.pending {
  background: #f3f4f6;
  color: #7d8490;
}

.topic-meta em.discussing {
  background: var(--blue-soft);
  color: var(--blue);
}

.topic-meta em.solved {
  background: #e7f9ef;
  color: var(--success);
}

.topic-card h2 {
  margin: 12px 0 8px;
  font-size: 18px;
  font-weight: 800;
  line-height: 1.4;
}

.topic-body {
  margin: 0;
  font-size: 14px;
  line-height: 1.75;
  color: #4d5767;
  white-space: pre-wrap;
}

.topic-card .tag-list {
  margin-top: 12px;
}

.ai-fail-banner {
  margin: 10px 0 0;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff7ed;
  color: #c2410c;
  font-size: 13px;
  line-height: 1.5;
}

.reply-section {
  margin-top: 18px;
  padding-left: 10px;
  border-left: 2px solid #e8ecf4;
}

.reply-label {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 700;
  color: #6b7485;
}

.reply-label span {
  min-width: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: #eef2f7;
  color: #5c6678;
  font-size: 11px;
  font-weight: 700;
  text-align: center;
}

.reply {
  position: relative;
  margin-bottom: 10px;
  padding: 10px 12px 10px 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e8ecf2;
}

.reply::before {
  content: '';
  position: absolute;
  left: 0;
  top: 10px;
  bottom: 10px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: #d5dbe6;
}

.reply.ai {
  background: linear-gradient(180deg, #f4f1ff 0%, #f8f9ff 56%);
  border-color: #ddd6ff;
}

.reply.ai::before {
  background: #7c6cf0;
}

.reply.accepted::before {
  background: var(--success);
}

.reply.ai.accepted {
  background: linear-gradient(180deg, #f4f1ff 0%, #f8f9ff 56%);
  border-color: #c8eed8;
}

.reply-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 8px;
}

.avatar.sm {
  width: 26px;
  height: 26px;
  font-size: 11px;
}

.avatar.bot {
  background: #ece7ff;
  color: #5b4dff;
}

.reply-meta b {
  font-size: 13px;
  font-weight: 700;
}

.reply-meta .kind {
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  background: #e8ecf2;
  color: #6b7485;
}

.reply-meta .kind.ai {
  background: #ece7ff;
  color: #5b4dff;
}

.reply-meta time {
  margin-left: auto;
  font-size: 11px;
  color: var(--muted);
}

.reply-meta i {
  font-size: 10px;
  font-style: normal;
  font-weight: 700;
  color: var(--success);
  background: #e7f9ef;
  padding: 2px 7px;
  border-radius: 999px;
}

.reply-body {
  margin: 8px 0 0 34px;
}

.ai-hint {
  margin: 0 0 6px;
  font-size: 11px;
  color: #7b74b0;
  line-height: 1.4;
}

.reply-body :deep(.markdown) {
  font-size: 13px;
  line-height: 1.7;
  color: #3e4755;
}

.reply-body :deep(.markdown p) {
  margin: 0 0 6px;
}

.reply-body :deep(.markdown p:last-child) {
  margin-bottom: 0;
}

.reply-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 0 34px;
  padding-top: 8px;
  border-top: 1px dashed #e4e8ef;
}

.reply.ai .reply-foot {
  border-top-color: #ddd6f8;
}

.reply-foot button {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  padding: 4px 0;
}

.reply-foot button.liked {
  color: var(--blue);
  font-weight: 600;
}

.answer-editor label {
  display: block;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #5c6678;
}
</style>
