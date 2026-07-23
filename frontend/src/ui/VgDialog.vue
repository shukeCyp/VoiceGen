<script setup>
import { dialogState, closeDialog } from './dialog'
import VgButton from './VgButton.vue'
import AliIcon from '../components/AliIcon.vue'

const iconByTone = {
  danger: 'clear',
  primary: 'check',
  default: 'check',
}

function onConfirm() {
  closeDialog(true)
}

function onCancel() {
  closeDialog(false)
}

function onMask(e) {
  if (e.target === e.currentTarget) {
    // alert: click mask = confirm; confirm: click mask = cancel
    closeDialog(dialogState.mode === 'alert')
  }
}

function onKeydown(e) {
  if (!dialogState.open) return
  if (e.key === 'Escape') {
    e.preventDefault()
    closeDialog(dialogState.mode === 'alert')
  } else if (e.key === 'Enter') {
    e.preventDefault()
    closeDialog(true)
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="dialogState.open"
      class="vg-dialog-mask"
      role="presentation"
      @mousedown="onMask"
      @keydown="onKeydown"
    >
      <div
        class="vg-dialog"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'vg-dialog-title'"
        tabindex="-1"
        ref="panel"
      >
        <div class="vg-dialog__head">
          <span
            class="vg-dialog__icon"
            :class="`vg-dialog__icon--${dialogState.tone || 'default'}`"
          >
            <AliIcon :name="iconByTone[dialogState.tone] || 'check'" :size="16" />
          </span>
          <h3 id="vg-dialog-title" class="vg-dialog__title">{{ dialogState.title }}</h3>
        </div>
        <div class="vg-dialog__body">
          {{ dialogState.message }}
        </div>
        <div class="vg-dialog__actions">
          <VgButton
            v-if="dialogState.mode === 'confirm'"
            variant="ghost"
            @click="onCancel"
          >
            {{ dialogState.cancelText }}
          </VgButton>
          <VgButton
            :variant="dialogState.tone === 'danger' ? 'danger' : 'primary'"
            @click="onConfirm"
          >
            {{ dialogState.confirmText }}
          </VgButton>
        </div>
      </div>
    </div>
  </Teleport>
</template>
