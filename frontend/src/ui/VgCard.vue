<script setup>
defineProps({
  title: { type: String, default: '' },
})
</script>

<template>
  <div class="vg-card">
    <h2 v-if="title || $slots.title" class="vg-card__title">
      <slot name="title">{{ title }}</slot>
    </h2>
    <slot />
  </div>
</template>
