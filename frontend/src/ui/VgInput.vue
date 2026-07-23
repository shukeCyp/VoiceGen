<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' },
  bare: { type: Boolean, default: false },
  min: { type: [String, Number], default: undefined },
  max: { type: [String, Number], default: undefined },
  step: { type: [String, Number], default: undefined },
})

const emit = defineEmits(['update:modelValue', 'change', 'input', 'blur', 'focus'])

function onInput(e) {
  const el = e.target
  let val = el.value
  if (el.type === 'number' && val !== '') {
    val = el.valueAsNumber
    if (Number.isNaN(val)) val = el.value
  }
  emit('update:modelValue', val)
  emit('input', e)
}

function onChange(e) {
  emit('change', e)
}
</script>

<template>
  <input
    class="vg-input"
    :class="{
      'vg-input--sm': size === 'sm',
      'vg-input--bare': bare,
    }"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :min="min"
    :max="max"
    :step="step"
    @input="onInput"
    @change="onChange"
    @blur="emit('blur', $event)"
    @focus="emit('focus', $event)"
  />
</template>
