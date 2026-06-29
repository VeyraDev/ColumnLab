<template>
  <div class="encoding-legend" aria-label="编码纹理图例">
    <div class="legend-item">
      <span class="swatch raw" />
      <span>RAW</span>
    </div>
    <div class="legend-item">
      <span class="swatch rle" />
      <span>RLE</span>
    </div>
    <div class="legend-item">
      <span class="swatch dict" />
      <span>DICT</span>
    </div>
  </div>
</template>

<style scoped>
.encoding-legend {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--text-tertiary);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.swatch {
  width: 14px;
  height: 14px;
  border: 1px solid var(--border-default);
  border-radius: 2px;
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
</style>
