<script setup>
defineProps({
  tone: { type: String, default: '' }, // '' | ok | warn | error
  dot: { type: Boolean, default: false },
})
</script>

<template>
  <span class="vg-badge" :class="tone ? `vg-badge--${tone}` : ''">
    <span v-if="dot" class="vg-badge__dot" />
    <slot />
  </span>
</template>
