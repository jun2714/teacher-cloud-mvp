<script setup>
defineProps({ title: { type: String, required: true }, back: { type: Boolean, default: false } })
</script>
<template>
  <header class="page-header">
    <button v-if="back" class="icon-button" @click="$router.back()">‹</button>
    <h1>{{ title }}</h1>
    <span v-if="back" class="header-space"></span>
  </header>
</template>
