<script setup>
defineProps({ kind: { type: String, default: 'document' } })
</script>

<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <template v-if="kind === 'write'">
      <path d="M12 5.5C9.4 4 6.4 3.6 3 4.5v14c3.4-.9 6.4-.5 9 1 2.6-1.5 5.6-1.9 9-1v-8M12 10v9.5" />
      <path d="m14.5 10.5.6-3 4.7-4.7a1.4 1.4 0 0 1 2 2l-4.7 4.7-2.6 1zM18.5 4l2 2M6 8.5l3 .6M6 12l3 .6" />
    </template>
    <template v-else>
      <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6z" />
      <path d="M14 3v6h6M8 13h8M8 17h5" />
    </template>
  </svg>
</template>

<style scoped>
svg { width: 24px; height: 24px; display: block; }
</style>
