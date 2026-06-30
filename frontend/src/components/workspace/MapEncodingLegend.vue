<template>
  <div class="map-encoding-legend" aria-label="编码与块状态图例">
    <div v-for="item in items" :key="item.key" class="legend-item" :title="item.label">
      <span class="swatch" :class="item.key" />
      <span class="legend-text">{{ item.label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
const items = [
  { key: 'raw', label: 'RAW' },
  { key: 'rle', label: 'RLE' },
  { key: 'dict', label: 'DICT' },
  { key: 'skipped', label: '跳过' },
  { key: 'scanned', label: '已扫描' },
  { key: 'active', label: '活动块' },
]
</script>

<style scoped>
.map-encoding-legend {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 8px;
  font-size: 10px;
  color: var(--text-tertiary);
  overflow: hidden;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.swatch {
  width: 12px;
  height: 12px;
  border: 1px solid var(--border-default);
  border-radius: 2px;
  flex-shrink: 0;
}

.swatch.raw {
  background: repeating-linear-gradient(
    -45deg,
    var(--bg-muted),
    var(--bg-muted) 2px,
    var(--bg-panel) 2px,
    var(--bg-panel) 4px
  );
}

.swatch.rle {
  background: repeating-linear-gradient(
    0deg,
    var(--bg-muted),
    var(--bg-muted) 2px,
    var(--bg-panel) 2px,
    var(--bg-panel) 4px
  );
}

.swatch.dict {
  background:
    radial-gradient(circle, var(--text-tertiary) 1px, transparent 1px);
  background-size: 4px 4px;
  background-color: var(--bg-panel);
}

.swatch.skipped {
  opacity: 0.45;
  background: repeating-linear-gradient(
    -45deg,
    var(--bg-muted),
    var(--bg-muted) 1px,
    transparent 1px,
    transparent 3px
  );
}

.swatch.scanned {
  border-color: var(--border-strong);
  background: var(--bg-panel);
}

.swatch.active {
  border: 2px solid var(--state-active-border);
  background: var(--state-active-bg);
}

.legend-text {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
