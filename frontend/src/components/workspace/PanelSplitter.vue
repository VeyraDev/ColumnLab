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
  position: absolute;
  z-index: 20;
  touch-action: none;
  background: transparent;
}

.panel-splitter.vertical {
  top: 0;
  bottom: 0;
  width: var(--workspace-panel-gap);
  margin-left: calc(var(--workspace-panel-gap) / -2);
  cursor: col-resize;
}

.panel-splitter.horizontal {
  left: 0;
  right: 0;
  height: var(--workspace-panel-gap);
  margin-top: calc(var(--workspace-panel-gap) / -2);
  cursor: row-resize;
}

.panel-splitter::after {
  content: '';
  position: absolute;
  background: transparent;
  transition: background 0.12s;
  pointer-events: none;
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

.panel-splitter::before {
  content: '';
  position: absolute;
}

.panel-splitter.vertical::before {
  top: 0;
  bottom: 0;
  left: 0;
  right: 0;
}

.panel-splitter.horizontal::before {
  left: 0;
  right: 0;
  top: 0;
  bottom: 0;
}
</style>
