<script setup>
import { nextTick, onMounted, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  rows: { type: [Number, String], default: 3 },
  bare: { type: Boolean, default: false },
  autoHeight: { type: Boolean, default: false },
  maxHeight: { type: Number, default: 280 },
})

const emit = defineEmits(['update:modelValue', 'input', 'blur', 'focus'])

let elRef = null

function setEl(el) {
  elRef = el
  if (props.autoHeight) resize()
}

function resize() {
  if (!elRef || !props.autoHeight) return
  elRef.style.height = 'auto'
  const next = Math.min(Math.max(elRef.scrollHeight, 40), props.maxHeight)
  elRef.style.height = `${next}px`
  elRef.style.overflowY = elRef.scrollHeight > props.maxHeight ? 'auto' : 'hidden'
}

function onInput(e) {
  emit('update:modelValue', e.target.value)
  emit('input', e)
  if (props.autoHeight) {
    nextTick(resize)
  }
}

watch(
  () => props.modelValue,
  () => {
    if (props.autoHeight) nextTick(resize)
  },
)

onMounted(() => {
  if (props.autoHeight) nextTick(resize)
})

defineExpose({ resize })
</script>

<template>
  <textarea
    :ref="setEl"
    class="vg-textarea"
    :class="{
      'vg-textarea--bare': bare,
      'vg-textarea--auto': autoHeight,
      'auto-h': autoHeight,
    }"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :rows="autoHeight ? 1 : rows"
    @input="onInput"
    @blur="emit('blur', $event)"
    @focus="emit('focus', $event)"
  />
</template>
