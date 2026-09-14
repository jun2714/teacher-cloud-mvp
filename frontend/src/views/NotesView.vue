<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { notesApi, reportsApi } from '../api'
import PageHeader from '../components/PageHeader.vue'

const router = useRouter()
const notes = ref([])
const reports = ref([])
const loading = ref(true)
const previewReports = computed(() => reports.value.slice(0, 3))

async function load() {
  loading.value = true
  try {
    ;[notes.value, reports.value] = await Promise.all([notesApi.list(), reportsApi.list()])
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <main class="sub-page">
    <PageHeader title="教研笔记" />
    <div class="page-body">
      <div class="intro"><h2>教研笔记</h2><p>记录教研学习中的所思所想所感</p></div>
      <section class="report-banner">
        <span class="report-icon">▤</span>
        <div>
          <b>研修总结报告</b>
          <small>根据笔记生成跟岗研修总结，含收获、反思与返校计划</small>
        </div>
        <button @click="router.push('/reports/generate')">生成总结</button>
      </section>
      <div class="list-title">
        <h3>我的总结</h3>
        <button type="button" class="text-link" @click="router.push('/reports')">全部 ›</button>
      </div>
      <article
        v-for="report in previewReports"
        :key="report.id"
        class="mini-report is-link"
        role="button"
        tabindex="0"
        @click="router.push(`/reports/${report.id}`)"
      >
        <span>▤</span>
        <div>
          <b>{{ report.title }}</b>
          <small>{{ report.source_note_ids?.length || 0 }} 篇笔记 · {{ new Date(report.created_at).toLocaleDateString() }}</small>
        </div>
        <em>已完成</em>
      </article>
      <article v-if="!reports.length" class="empty-card">还没有生成总结报告</article>
      <div class="list-title"><h3>每日笔记</h3><span>{{ notes.length }} 篇</span></div>
      <div v-if="loading" class="loading-card">加载中…</div>
      <article v-else-if="!notes.length" class="empty-card">还没有笔记，点击右下角新建</article>
      <article
        v-for="note in notes"
        :key="note.id"
        class="note-card is-link"
        role="button"
        tabindex="0"
        @click="router.push(`/notes/${note.id}`)"
      >
        <div class="note-meta">
          <span>{{ note.category_label }}</span>
          <time>{{ new Date(note.created_at).toLocaleDateString() }}</time>
        </div>
        <h3>{{ note.title }}</h3>
        <p>{{ note.content }}</p>
        <div class="tag-list"><span v-for="tag in note.tags" :key="tag">{{ tag }}</span></div>
      </article>
    </div>
  </main>
</template>
