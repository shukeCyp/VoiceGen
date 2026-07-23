<script setup>
defineProps({
  label: { type: String, default: '' },
  hint: { type: String, default: '' },
})
</script>

<template>
  <div class="vg-field">
    <label v-if="label || $slots.label" class="vg-field__label">
      <slot name="label">{{ label }}</slot>
    </label>
    <slot />
    <div v-if="hint || $slots.hint" class="vg-field__hint">
      <slot name="hint">{{ hint }}</slot>
    </div>
  </div>
</template>
