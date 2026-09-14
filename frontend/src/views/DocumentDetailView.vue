<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { lessonApi, reportsApi } from '../api'
import PageHeader from '../components/PageHeader.vue'
import MarkdownBlock from '../components/MarkdownBlock.vue'
import { downloadBlob } from '../utils/download'
import { errorMessage, showAlert, showConfirm } from '../utils/dialog'

const route = useRoute()
const router = useRouter()
const kind = computed(() => route.meta.kind || 'report')
const item = ref(null)
const loading = ref(true)
const downloading = ref(false)
const editing = ref(false)
const saving = ref(false)
const removing = ref(false)
const draft = ref('')

const pageTitle = computed(() => {
  if (kind.value === 'lesson') return '个人教学设计'
  if (kind.value === 'review') return '听评课报告'
  return '研修总结报告'
})
const content = computed(() => item.value?.generated_content || item.value?.report_content || item.value?.content || '')
const listTo = computed(() => {
  if (kind.value === 'lesson') return '/lesson-plans'
  if (kind.value === 'review') return '/lesson-reviews'
  return '/reports'
})

onMounted(async () => {
  try {
    if (kind.value === 'lesson') item.value = await lessonApi.detail(route.params.id)
    else if (kind.value === 'review') item.value = await lessonApi.detailReview(route.params.id)
    else item.value = await reportsApi.detail(route.params.id)
  } catch (e) {
    showAlert(errorMessage(e, '记录不存在或已删除'), 'error')
    router.replace(listTo.value)
  } finally {
    loading.value = false
  }
})

function startEdit() {
  draft.value = content.value
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  draft.value = content.value
}

async function saveEdit() {
  if (!item.value?.id) return
  saving.value = true
  try {
    if (kind.value === 'lesson') {
      item.value = await lessonApi.savePlan(item.value.id, { generated_content: draft.value })
    } else if (kind.value === 'review') {
      item.value = await lessonApi.saveReview(item.value.id, { report_content: draft.value })
    } else {
      item.value = await reportsApi.save(item.value.id, { content: draft.value })
    }
    editing.value = false
    showAlert('已保存修改')
  } catch (e) {
    showAlert(errorMessage(e, '保存失败'), 'error')
  } finally {
    saving.value = false
  }
}

async function removeItem() {
  if (!item.value?.id) return
  const ok = await showConfirm(`删除「${item.value.title || pageTitle.value}」？删除后不可恢复。`)
  if (!ok) return
  removing.value = true
  try {
    if (kind.value === 'lesson') await lessonApi.remove(item.value.id)
    else if (kind.value === 'review') await lessonApi.removeReview(item.value.id)
    else await reportsApi.remove(item.value.id)
    router.replace(listTo.value)
  } catch (e) {
    showAlert(errorMessage(e, '删除失败'), 'error')
  } finally {
    removing.value = false
  }
}

async function downloadWord() {
  if (!item.value?.id) return
  downloading.value = true
  try {
    const res = kind.value === 'lesson'
      ? await lessonApi.exportPlan(item.value.id)
      : kind.value === 'review'
        ? await lessonApi.exportReview(item.value.id)
        : await reportsApi.exportDocx(item.value.id)
    await downloadBlob(res, `${item.value.title || pageTitle.value}.docx`)
  } catch (e) {
    showAlert(errorMessage(e, '导出失败'), 'error')
  } finally {
    downloading.value = false
  }
}
</script>

<template>
  <main class="sub-page">
    <PageHeader :title="pageTitle" back />
    <div class="page-body">
      <div v-if="loading" class="loading-card">加载中…</div>
      <template v-else-if="item">
        <section class="result-toolbar detail-head">
          <div>
            <b>{{ item.title }}</b>
            <small>{{ new Date(item.created_at).toLocaleString() }}</small>
          </div>
          <button type="button" class="secondary-button" :disabled="downloading || editing" @click="downloadWord">
            {{ downloading ? '正在导出…' : '下载 Word' }}
          </button>
        </section>
        <section class="result-card">
          <textarea v-if="editing" v-model="draft" class="edit-area" rows="18" />
          <MarkdownBlock v-else :content="content" />
        </section>
        <div class="detail-actions">
          <template v-if="editing">
            <button type="button" class="primary-button" :class="{ 'orange-button': kind === 'lesson' }" :disabled="saving" @click="saveEdit">
              {{ saving ? '保存中…' : '保存修改' }}
            </button>
            <button type="button" class="secondary-button" :disabled="saving" @click="cancelEdit">取消</button>
          </template>
          <button v-else type="button" class="secondary-button" @click="startEdit">编辑内容</button>
          <button
            v-if="!editing"
            type="button"
            class="danger-button"
            :disabled="removing || downloading"
            @click="removeItem"
          >{{ removing ? '删除中…' : '删除' }}</button>
        </div>
      </template>
    </div>
  </main>
</template>

<style scoped>
.detail-head {
  margin-bottom: 12px;
  align-items: flex-start;
}
.detail-head div {
  min-width: 0;
}
.detail-head b {
  display: block;
  font-size: 15px;
  line-height: 1.4;
}
.detail-head small {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
}
.edit-area {
  width: 100%;
  min-height: 360px;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px;
  font-size: 14px;
  line-height: 1.7;
  resize: vertical;
  box-sizing: border-box;
}
.detail-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  padding-bottom: 12px;
}
.detail-actions .secondary-button,
.detail-actions .primary-button,
.detail-actions .danger-button {
  width: 100%;
  min-height: 44px;
}

.danger-button {
  border: 0;
  border-radius: 12px;
  background: #fff1f0;
  color: #f04438;
  font-weight: 700;
}
</style>
