<script setup>
/**
 * 阿里 iconfont 风格 SVG 图标（本地 symbol，离线可用）
 * 图标路径参考 iconfont.cn 常用线性图标结构
 */
defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 16 },
})
</script>

<template>
  <svg
    class="ali-icon"
    :width="size"
    :height="size"
    aria-hidden="true"
  >
    <use :href="`#ali-icon-${name}`" />
  </svg>
</template>
