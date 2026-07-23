<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue', 'change'])

function onChange(e) {
  const v = e.target.checked
  emit('update:modelValue', v)
  emit('change', v)
}
</script>

<template>
  <label class="vg-checkbox">
    <input type="checkbox" :checked="modelValue" :disabled="disabled" @change="onChange" />
  </label>
</template>
