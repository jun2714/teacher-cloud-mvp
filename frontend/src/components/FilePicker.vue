<script setup>
import { ref } from 'vue'

const props = defineProps({
  accept: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  filename: { type: String, default: '' },
  buttonText: { type: String, default: '选择文件' },
  hint: { type: String, default: '' },
})

const emit = defineEmits(['change', 'clear'])
const inputRef = ref(null)

function open() {
  if (!props.disabled) inputRef.value?.click()
}

function onChange(event) {
  const file = event.target.files?.[0] || null
  emit('change', file)
}

function clear() {
  if (inputRef.value) inputRef.value.value = ''
  emit('clear')
}
</script>

<template>
  <div class="file-picker" :class="{ disabled, chosen: Boolean(filename) }">
    <input
      ref="inputRef"
      class="file-picker-input"
      type="file"
      :accept="accept"
      :disabled="disabled"
      @change="onChange"
    />
    <button class="file-picker-btn" type="button" :disabled="disabled" @click="open">
      <span class="file-picker-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path d="M12 16V6M12 6l-3.5 3.5M12 6l3.5 3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M5 18.5h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
        </svg>
      </span>
      <span class="file-picker-texts">
        <b>{{ filename ? '重新选择' : buttonText }}</b>
        <em>{{ filename || '点击选择文件' }}</em>
      </span>
    </button>
    <button
      v-if="filename"
      class="file-picker-clear"
      type="button"
      :disabled="disabled"
      @click="clear"
    >清除</button>
    <small v-if="hint">{{ hint }}</small>
  </div>
</template>

<style scoped>
.file-picker {
  position: relative;
  margin-top: 8px;
}

.file-picker-input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.file-picker-btn {
  width: 100%;
  min-height: 56px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid #d6e6ff;
  border-radius: 12px;
  background: #fff;
  text-align: left;
}

.file-picker-icon {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: #e8f1ff;
  color: #1a6dff;
}

.file-picker-icon svg {
  width: 18px;
  height: 18px;
}

.file-picker-texts {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-picker-texts b {
  font-size: 14px;
  font-weight: 700;
  color: #1a6dff;
  line-height: 1.3;
}

.file-picker-texts em {
  font-size: 12px;
  font-style: normal;
  font-weight: 500;
  color: #8a93a3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-picker.chosen .file-picker-texts em {
  color: #1a2332;
}

.file-picker-btn:active:not(:disabled) {
  background: #e8f1ff;
}

.file-picker-btn:disabled {
  opacity: 0.55;
}

.file-picker-clear {
  margin-top: 8px;
  border: 0;
  background: none;
  color: #f04438;
  font-size: 12px;
  font-weight: 700;
  padding: 0;
}

.file-picker small {
  display: block;
  margin-top: 6px;
  font-size: 11px;
  font-weight: 500;
  color: #8a93a3;
  line-height: 1.55;
}
</style>
