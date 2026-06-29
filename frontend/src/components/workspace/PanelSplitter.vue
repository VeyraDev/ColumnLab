<script setup lang="ts">
defineProps<{
  orientation: 'horizontal' | 'vertical'
  title?: string
}>()

const emit = defineEmits<{
  resizeStart: [event: PointerEvent]
}>()
</script>

<template>
  <div
    class="panel-splitter"
    :class="orientation"
    role="separator"
    :aria-orientation="orientation"
    :title="title"
    @pointerdown="emit('resizeStart', $event)"
  />
</template>

<style scoped>
.panel-splitter {
  position: relative;
  flex-shrink: 0;
  z-index: 20;
  touch-action: none;
}

.panel-splitter.vertical {
  width: 10px;
  margin: 0 -2px;
  cursor: col-resize;
}

.panel-splitter.horizontal {
  height: 10px;
  margin: -2px 0;
  cursor: row-resize;
}

.panel-splitter::after {
  content: '';
  position: absolute;
  background: var(--border-default);
  transition: background 0.12s;
}

.panel-splitter.vertical::after {
  top: 0;
  bottom: 0;
  left: 50%;
  width: 1px;
  transform: translateX(-50%);
}

.panel-splitter.horizontal::after {
  left: 0;
  right: 0;
  top: 50%;
  height: 1px;
  transform: translateY(-50%);
}

.panel-splitter:hover::after,
.panel-splitter:active::after {
  background: var(--accent);
}

.panel-splitter.vertical:hover::after,
.panel-splitter.vertical:active::after {
  width: 2px;
}

.panel-splitter.horizontal:hover::after,
.panel-splitter.horizontal:active::after {
  height: 2px;
}

.panel-splitter::before {
  content: '';
  position: absolute;
}

.panel-splitter.vertical::before {
  top: 0;
  bottom: 0;
  left: -3px;
  right: -3px;
}

.panel-splitter.horizontal::before {
  left: 0;
  right: 0;
  top: -3px;
  bottom: -3px;
}
</style>
