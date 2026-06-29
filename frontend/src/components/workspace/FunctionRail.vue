<script setup lang="ts">
defineProps<{
  active?: boolean
  icon: string
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
    <span class="rail-icon" aria-hidden="true">{{ icon }}</span>
    <span class="rail-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.rail-btn {
  width: 100%;
  min-height: 52px;
  border: 1px solid transparent;
  border-radius: var(--radius-control);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 6px 2px;
}

.rail-btn:hover {
  background: var(--bg-panel);
  color: var(--text-primary);
}

.rail-btn.active {
  background: var(--bg-panel);
  border-color: var(--border-default);
  color: var(--text-primary);
}

.rail-icon {
  font-size: 14px;
  line-height: 1;
}

.rail-label {
  font-size: 10px;
  line-height: 1.2;
  text-align: center;
}
</style>
