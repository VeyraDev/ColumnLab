<script setup lang="ts">
import type { Component } from 'vue'

defineProps<{
  active?: boolean
  icon: Component
  label: string
  title: string
}>()

const emit = defineEmits<{
  click: []
}>()
</script>

<template>
  <button
    type="button"
    class="rail-btn"
    :class="{ active }"
    :title="title"
    :aria-label="title"
    @click="emit('click')"
  >
    <component :is="icon" class="rail-icon" :size="22" :stroke-width="1.5" aria-hidden="true" />
    <span class="rail-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.rail-btn {
  position: relative;
  width: 100%;
  min-height: 48px;
  border: none;
  border-radius: 0;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 4px 2px;
}

.rail-btn:hover {
  background: var(--bg-panel);
  color: var(--text-primary);
}

.rail-icon {
  flex-shrink: 0;
}

.rail-btn.active {
  background: var(--bg-panel);
  color: var(--text-primary);
}

.rail-btn.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 2px;
  background: var(--accent);
  border-radius: 0 1px 1px 0;
}

.rail-label {
  font-size: 9px;
  line-height: 1.15;
  text-align: center;
}
</style>
