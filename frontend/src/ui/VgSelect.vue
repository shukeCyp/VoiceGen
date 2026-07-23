<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AliIcon from '../components/AliIcon.vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean, null], default: '' },
  /** [{ value, label, disabled? }] or string[] */
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择' },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' }, // md | sm
  bare: { type: Boolean, default: false },
  inline: { type: Boolean, default: false },
  searchable: { type: Boolean, default: false },
  clearable: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const rootEl = ref(null)
const triggerEl = ref(null)
const dropdownEl = ref(null)
const search = ref('')
const panelStyle = ref({})

const normalized = computed(() =>
  (props.options || []).map((item) => {
    if (item != null && typeof item === 'object') {
      return {
        value: item.value,
        label: item.label ?? String(item.value ?? ''),
        disabled: Boolean(item.disabled),
      }
    }
    return { value: item, label: String(item), disabled: false }
  }),
)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return normalized.value
  return normalized.value.filter(
    (o) =>
      String(o.label).toLowerCase().includes(q) ||
      String(o.value).toLowerCase().includes(q),
  )
})

const selected = computed(() =>
  normalized.value.find((o) => o.value === props.modelValue),
)

const displayLabel = computed(() => selected.value?.label || '')

function updatePosition() {
  const trigger = triggerEl.value
  if (!trigger) return
  const rect = trigger.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight
  const width = Math.max(rect.width, 140)
  const maxH = 280
  const spaceBelow = vh - rect.bottom - 8
  const spaceAbove = rect.top - 8
  const placeAbove = spaceBelow < 160 && spaceAbove > spaceBelow
  const height = Math.min(maxH, placeAbove ? spaceAbove : spaceBelow)

  let left = rect.left
  if (left + width > vw - 8) left = Math.max(8, vw - width - 8)

  panelStyle.value = {
    left: `${left}px`,
    width: `${width}px`,
    maxHeight: `${Math.max(120, height)}px`,
    ...(placeAbove
      ? { bottom: `${vh - rect.top + 4}px`, top: 'auto' }
      : { top: `${rect.bottom + 4}px`, bottom: 'auto' }),
  }
}

function openMenu() {
  if (props.disabled) return
  open.value = true
  search.value = ''
  nextTick(() => {
    updatePosition()
    if (props.searchable) {
      dropdownEl.value?.querySelector('input')?.focus()
    }
  })
}

function closeMenu() {
  open.value = false
  search.value = ''
}

function toggle() {
  if (open.value) closeMenu()
  else openMenu()
}

function pick(opt) {
  if (opt.disabled) return
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  closeMenu()
}

function onDocPointer(e) {
  if (!open.value) return
  const t = e.target
  if (rootEl.value?.contains(t) || dropdownEl.value?.contains(t)) return
  closeMenu()
}

function onKey(e) {
  if (!open.value) return
  if (e.key === 'Escape') {
    e.preventDefault()
    closeMenu()
  }
}

function onScrollOrResize() {
  if (open.value) updatePosition()
}

onMounted(() => {
  document.addEventListener('mousedown', onDocPointer, true)
  document.addEventListener('keydown', onKey, true)
  window.addEventListener('resize', onScrollOrResize)
  window.addEventListener('scroll', onScrollOrResize, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', onDocPointer, true)
  document.removeEventListener('keydown', onKey, true)
  window.removeEventListener('resize', onScrollOrResize)
  window.removeEventListener('scroll', onScrollOrResize, true)
})

watch(
  () => props.disabled,
  (v) => {
    if (v) closeMenu()
  },
)
</script>

<template>
  <div
    ref="rootEl"
    class="vg-select"
    :class="{
      'is-open': open,
      'vg-select--sm': size === 'sm',
      'vg-select--bare': bare,
      'vg-select--inline': inline,
    }"
  >
    <button
      ref="triggerEl"
      type="button"
      class="vg-select__trigger"
      :disabled="disabled"
      :title="displayLabel || placeholder"
      @click="toggle"
    >
      <span class="vg-select__label" :class="{ 'is-placeholder': !selected }">
        {{ displayLabel || placeholder }}
      </span>
      <span class="vg-select__caret">
        <AliIcon name="arrow-down" :size="12" />
      </span>
    </button>

    <Teleport to="body">
      <div
        v-if="open"
        ref="dropdownEl"
        class="vg-select__dropdown"
        :style="panelStyle"
        @mousedown.prevent
      >
        <div v-if="searchable" class="vg-select__search">
          <input
            v-model="search"
            type="text"
            placeholder="搜索…"
            @keydown.stop
          />
        </div>
        <div v-if="!filtered.length" class="vg-select__empty">无选项</div>
        <button
          v-for="opt in filtered"
          :key="String(opt.value)"
          type="button"
          class="vg-select__option"
          :class="{ 'is-active': opt.value === modelValue }"
          :disabled="opt.disabled"
          @click="pick(opt)"
        >
          {{ opt.label }}
        </button>
      </div>
    </Teleport>
  </div>
</template>
