<template>
  <section class="storage-map-placeholder">
    <div class="panel-header">
      <span>列块存储映射</span>
      <div class="legend">
        <span>RAW</span>
        <span>RLE</span>
        <span>DICT</span>
        <span>跳过</span>
        <span>扫描</span>
        <span>活动块</span>
      </div>
    </div>
    <div class="map-body">
      <p>导入数据并选择数据集后，将在此渲染列块轨道与编码纹理。</p>
      <div class="grid-preview" aria-hidden="true">
        <div v-for="n in 6" :key="n" class="track-row">
          <span class="track-label">col_{{ n }}</span>
          <div class="track-blocks">
            <span v-for="b in 12" :key="b" class="block-cell" />
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.storage-map-placeholder {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--bg-raised);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid var(--border-default);
  gap: 8px;
  flex-wrap: wrap;
}

.legend {
  display: flex;
  gap: 10px;
  font-weight: 400;
  font-size: 11px;
  color: var(--text-tertiary);
}

.map-body {
  flex: 1;
  overflow: auto;
  padding: 12px;
  min-height: 0;
}

.map-body p {
  margin: 0 0 12px;
  color: var(--text-secondary);
  font-size: 12px;
}

.grid-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.track-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 8px;
  align-items: center;
}

.track-label {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
}

.track-blocks {
  display: flex;
  gap: 2px;
  flex-wrap: wrap;
}

.block-cell {
  width: 14px;
  height: 14px;
  border: 1px solid var(--border-default);
  border-radius: 2px;
  background: repeating-linear-gradient(
    -45deg,
    var(--bg-muted),
    var(--bg-muted) 2px,
    var(--bg-panel) 2px,
    var(--bg-panel) 4px
  );
}
</style>
