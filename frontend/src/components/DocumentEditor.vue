<script setup>
import { watch } from 'vue'
import { EditorContent, useEditor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import { TableKit } from '@tiptap/extension-table'
import Image from '@tiptap/extension-image'
import { Markdown } from '@tiptap/markdown'

const props = defineProps({
  modelValue: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
const editor = useEditor({
  extensions: [
    StarterKit.configure({
      underline: false,
      link: { openOnClick: false },
    }),
    TableKit.configure({ table: { renderWrapper: true } }),
    Image,
    // Generated teacher details use one line per field; retain those line breaks.
    Markdown.configure({ markedOptions: { gfm: true, breaks: true } }),
  ],
  content: props.modelValue,
  contentType: 'markdown',
  editable: !props.disabled,
  editorProps: {
    attributes: {
      role: 'textbox',
      'aria-label': '文档正文',
      'aria-multiline': 'true',
      spellcheck: 'false',
    },
  },
  // Do not normalize stored content merely by opening and saving the editor.
  onUpdate: ({ editor: current }) => emit('update:modelValue', current.getMarkdown()),
})

watch(() => props.disabled, (disabled) => editor.value?.setEditable(!disabled, false))

function setParagraphStyle(event) {
  const level = Number(event.target.value)
  if (level) editor.value.chain().focus().setHeading({ level }).run()
  else editor.value.chain().focus().setParagraph().run()
}
</script>

<template>
  <div class="document-editor">
    <p class="editor-hint">直接点击正文修改，标题、加粗和表格会保留。修改后请保存。</p>
    <template v-if="editor">
      <div class="editor-tools" role="group" aria-label="文字格式">
        <select aria-label="段落样式" :disabled="disabled"
          :value="editor.isActive('heading') ? editor.getAttributes('heading').level : 0"
          @change="setParagraphStyle">
          <option :value="0">正文</option>
          <option :value="1">一级标题</option>
          <option :value="2">二级标题</option>
          <option :value="3">三级标题</option>
        </select>
        <button type="button" :disabled="disabled" :aria-pressed="editor.isActive('bold')"
          @mousedown.prevent @click="editor.chain().focus().toggleBold().run()">加粗</button>
        <button type="button" :disabled="disabled" :aria-pressed="editor.isActive('bulletList')"
          @mousedown.prevent @click="editor.chain().focus().toggleBulletList().run()">列表</button>
        <button type="button" :disabled="disabled" :aria-pressed="editor.isActive('orderedList')"
          @mousedown.prevent @click="editor.chain().focus().toggleOrderedList().run()">编号</button>
        <button type="button" :disabled="disabled || !editor.can().undo()"
          @mousedown.prevent @click="editor.chain().focus().undo().run()">撤销</button>
        <button type="button" :disabled="disabled || !editor.can().redo()"
          @mousedown.prevent @click="editor.chain().focus().redo().run()">重做</button>
      </div>
      <div v-if="editor.isActive('table')" class="editor-tools table-tools" role="group" aria-label="表格操作">
        <span>当前表格</span>
        <button type="button" :disabled="disabled" @mousedown.prevent @click="editor.chain().focus().addRowAfter().run()">加一行</button>
        <button type="button" :disabled="disabled" @mousedown.prevent @click="editor.chain().focus().addColumnAfter().run()">加一列</button>
      </div>
      <EditorContent :editor="editor" class="editor-scroll" />
    </template>
  </div>
</template>

<style scoped>
.document-editor { min-width: 0; }
.editor-hint { margin: 0 0 12px; color: var(--muted); font-size: 13px; line-height: 1.6; }
.editor-tools { display: flex; flex-wrap: wrap; gap: 8px; padding: 10px; background: #f5f7fb; border: 1px solid var(--line); border-radius: 12px 12px 0 0; }
.editor-tools button, .editor-tools select { min-height: 44px; padding: 0 12px; border: 1px solid var(--line); border-radius: 8px; background: #fff; color: #26364c; font: inherit; font-size: 14px; cursor: pointer; }
.editor-tools button[aria-pressed="true"] { background: var(--blue-soft); border-color: var(--blue); color: var(--blue); }
.editor-tools button:disabled, .editor-tools select:disabled { opacity: .45; cursor: default; }
.editor-tools :focus-visible { outline: 2px solid var(--blue); outline-offset: 2px; }
.table-tools { border-radius: 0; border-top: 0; align-items: center; }
.table-tools span { font-size: 12px; color: var(--muted); }
.editor-scroll { max-height: 62vh; min-height: 320px; overflow-y: auto; border: 1px solid var(--line); border-top: 0; border-radius: 0 0 12px 12px; background: #fff; overscroll-behavior: contain; }
.editor-scroll:focus-within { border-color: var(--blue); }
.editor-scroll :deep(.tiptap) { min-height: 320px; padding: 16px; outline: none; font-size: 16px; line-height: 1.8; color: #3e4755; overflow-wrap: anywhere; }
.editor-scroll :deep(.tiptap > :first-child) { margin-top: 0; }
.editor-scroll :deep(p) { margin: 0 0 10px; }
.editor-scroll :deep(h1) { font-size: 22px; line-height: 1.5; color: #172c4c; }
.editor-scroll :deep(h2) { font-size: 19px; line-height: 1.5; color: #172c4c; }
.editor-scroll :deep(h3), .editor-scroll :deep(h4), .editor-scroll :deep(h5), .editor-scroll :deep(h6) { font-size: 17px; line-height: 1.5; color: #172c4c; }
.editor-scroll :deep(blockquote) { margin: 12px 0; padding: 10px 12px; border-left: 3px solid var(--blue); background: var(--blue-soft); }
.editor-scroll :deep(ul), .editor-scroll :deep(ol) { padding-left: 24px; }
.editor-scroll :deep(pre) { white-space: pre-wrap; padding: 12px; background: #f5f7fb; border-radius: 8px; }
.editor-scroll :deep(img) { max-width: 100%; height: auto; }
.editor-scroll :deep(.tableWrapper) { overflow-x: auto; margin: 12px 0; }
.editor-scroll :deep(table) { border-collapse: collapse; table-layout: fixed; min-width: 560px; width: 100%; font-size: 14px; }
.editor-scroll :deep(td), .editor-scroll :deep(th) { border: 1px solid #cbd5e1; padding: 8px; vertical-align: top; position: relative; min-width: 100px; }
.editor-scroll :deep(th) { background: #eef3fb; }
.editor-scroll :deep(.selectedCell) { background: #e2edff; }
</style>
