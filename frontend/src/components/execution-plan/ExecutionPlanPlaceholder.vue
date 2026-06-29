<template>
  <section class="execution-plan">
    <div class="plan-grid">
      <div class="plan-col">
        <div class="section-title">执行轨迹（物理计划）</div>
        <pre class="plan-tree mono">Aggregate [等待查询]
└─ Project
   └─ BlockScan [— / — blocks]</pre>
      </div>
      <div class="plan-col stats">
        <div class="section-title">执行统计</div>
        <ul>
          <li>扫描块：— / —</li>
          <li>跳过块：—</li>
          <li>解码块：—</li>
          <li>读取数据：—</li>
          <li>耗时：—</li>
        </ul>
      </div>
      <div class="plan-col">
        <div class="section-title">筛选条件</div>
        <p class="mono filter-sql">—</p>
        <div class="section-title">运行状态</div>
        <p>空闲</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.execution-plan {
  background: var(--bg-panel);
  border-top: 1px solid var(--border-default);
  min-height: 0;
  overflow: auto;
}

.plan-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr) minmax(0, 0.8fr);
  gap: 0;
  min-height: 140px;
}

.plan-col {
  padding: 8px 10px;
  border-right: 1px solid var(--border-default);
  font-size: 12px;
}

.plan-col:last-child {
  border-right: none;
}

.section-title {
  font-weight: 600;
  font-size: 11px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.plan-tree {
  margin: 0;
  font-size: 11px;
  line-height: 1.6;
  color: var(--text-primary);
  white-space: pre-wrap;
}

.stats ul {
  margin: 0;
  padding: 0;
  list-style: none;
  color: var(--text-secondary);
  line-height: 1.7;
}

.filter-sql {
  margin: 0 0 10px;
  font-size: 11px;
  color: var(--text-tertiary);
}
</style>
