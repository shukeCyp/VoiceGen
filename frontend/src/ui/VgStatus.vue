<script setup>
defineProps({
  status: { type: String, default: 'idle' },
})
</script>

<template>
  <span class="vg-status" :class="`vg-status--${status || 'idle'}`">
    <slot />
  </span>
</template>
