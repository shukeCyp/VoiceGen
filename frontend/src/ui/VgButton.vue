<script setup>
import AliIcon from '../components/AliIcon.vue'

defineProps({
  variant: { type: String, default: 'default' }, // default | primary | danger | ghost
  size: { type: String, default: 'md' }, // md | sm
  icon: { type: String, default: '' },
  iconSize: { type: [Number, String], default: 14 },
  iconOnly: { type: Boolean, default: false },
  fab: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  title: { type: String, default: '' },
})
</script>

<template>
  <button
    :type="type"
    class="vg-btn"
    :class="[
      variant !== 'default' ? `vg-btn--${variant}` : '',
      size === 'sm' ? 'vg-btn--sm' : '',
      iconOnly ? 'vg-btn--icon-only' : '',
      fab ? 'vg-btn--fab' : '',
    ]"
    :disabled="disabled"
    :title="title"
  >
    <AliIcon v-if="icon" :name="icon" :size="iconSize" />
    <slot />
  </button>
</template>
