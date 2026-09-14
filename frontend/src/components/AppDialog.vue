<script setup>
import { useDialogStore } from '../stores/dialog'

const dialog = useDialogStore()

const icons = {
  warning: '!',
  error: '!',
  success: '✓',
  info: 'i',
}
</script>

<template>
  <Teleport to="body">
    <Transition name="app-dialog">
      <div
        v-if="dialog.visible"
        class="app-dialog-mask"
        @click.self="dialog.mode === 'alert' && dialog.close(true)"
      >
        <div class="app-dialog" role="dialog" aria-modal="true">
          <span class="app-dialog-icon" :class="dialog.type">{{ icons[dialog.type] || '!' }}</span>
          <h3>{{ dialog.title }}</h3>
          <p>{{ dialog.message }}</p>
          <div class="app-dialog-actions" :class="{ pair: dialog.mode === 'confirm' }">
            <button v-if="dialog.mode === 'confirm'" type="button" class="ghost-button" @click="dialog.close(false)">取消</button>
            <button type="button" class="ok-button" @click="dialog.close(true)">确定</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.app-dialog-mask {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: min(100%, var(--app-w, 430px));
  z-index: 3000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(4px);
}

.app-dialog {
  width: min(100%, 320px);
  background: #fff;
  border-radius: 20px;
  padding: 22px 20px 16px;
  text-align: center;
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.22);
}

.app-dialog-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin: 0 auto 12px;
  border-radius: 50%;
  font-size: 20px;
  font-weight: 800;
  color: #fff;
}

.app-dialog-icon.warning,
.app-dialog-icon.info {
  background: linear-gradient(135deg, #f5a524, #f79009);
}

.app-dialog-icon.error {
  background: linear-gradient(135deg, #f97066, #f04438);
}

.app-dialog-icon.success {
  background: linear-gradient(135deg, #32d583, #12b76a);
}

.app-dialog h3 {
  margin: 0 0 8px;
  font-size: 17px;
  font-weight: 800;
  color: #1a2332;
}

.app-dialog p {
  margin: 0 0 18px;
  font-size: 14px;
  line-height: 1.6;
  color: #5c6678;
}

.app-dialog-actions {
  display: grid;
  gap: 8px;
}

.app-dialog-actions.pair {
  grid-template-columns: 1fr 1fr;
}

.ok-button,
.ghost-button {
  width: 100%;
  min-height: 44px;
  border: 0;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 700;
}

.ok-button {
  background: linear-gradient(135deg, #1a6dff, #0d4fd6);
  color: #fff;
  box-shadow: 0 8px 18px rgba(26, 109, 255, 0.28);
}

.ghost-button {
  background: #f3f5f8;
  color: #5c6678;
}

.app-dialog-enter-active,
.app-dialog-leave-active {
  transition: opacity 0.18s ease;
}

.app-dialog-enter-active .app-dialog,
.app-dialog-leave-active .app-dialog {
  transition: transform 0.18s ease, opacity 0.18s ease;
}

.app-dialog-enter-from,
.app-dialog-leave-to {
  opacity: 0;
}

.app-dialog-enter-from .app-dialog,
.app-dialog-leave-to .app-dialog {
  transform: scale(0.92) translateY(8px);
  opacity: 0;
}
</style>
