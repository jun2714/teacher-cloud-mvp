<script setup>
import AppDialog from './components/AppDialog.vue'
import NoticeToast from './components/NoticeToast.vue'
</script>

<template>
  <router-view />
  <AppDialog />
  <NoticeToast />
</template>
