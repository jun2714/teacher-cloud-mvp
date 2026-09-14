<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '可选择或填写' },
  maxlength: { type: [Number, String], default: 40 },
})

const emit = defineEmits(['update:modelValue'])
const open = ref(false)
const root = ref(null)
const typing = ref(false)

const filtered = computed(() => {
  if (!typing.value) return props.options
  const q = String(props.modelValue || '').trim()
  if (!q) return props.options
  return props.options.filter((item) => item.includes(q))
})

function setValue(value) {
  typing.value = true
  emit('update:modelValue', value)
}

function pick(item) {
  typing.value = false
  emit('update:modelValue', item)
  open.value = false
}

function toggleMenu() {
  typing.value = false
  open.value = !open.value
}

function onFocus() {
  typing.value = false
  open.value = true
}

function onDocClick(e) {
  if (!root.value?.contains(e.target)) open.value = false
}

onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<template>
  <div ref="root" class="suggest">
    <input
      :value="modelValue"
      :placeholder="placeholder"
      :maxlength="maxlength"
      autocomplete="off"
      @input="setValue($event.target.value)"
      @focus="onFocus"
    />
    <button class="suggest-caret" type="button" tabindex="-1" aria-label="打开选项" @click.stop="toggleMenu">▾</button>
    <ul v-if="open" class="suggest-menu">
      <li
        v-for="item in filtered"
        :key="item"
        :class="{ active: item === modelValue }"
        @mousedown.prevent="pick(item)"
      >{{ item }}</li>
      <li v-if="!filtered.length" class="suggest-empty" @mousedown.prevent="open = false">
        使用「{{ modelValue }}」
      </li>
    </ul>
  </div>
</template>
