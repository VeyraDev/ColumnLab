# ColumnLab UI 视觉重构任务包 · Batch 1

## 0. 任务模式

**模式：已有参考图 + 已有代码的渐进式视觉重构**

事实源优先级：

1. 现有 Vue / Pinia / API 代码决定业务行为与数据结构。
2. 已确认的效果图决定静态视觉、布局比例和信息密度。
3. 本文决定实现约束与验收方式。

本批次只处理 **Workspace / 存储映射主界面**。  
不得同时重构导入、查询、压缩实验和性能基准页面。

---

## 1. 为什么第一批不先改颜色

当前项目的基础颜色已经是低饱和、偏橄榄灰的中性色体系，且已经采用：

- 小圆角；
- 无常驻大阴影；
- 低饱和强调色；
- 13px 紧凑界面字号；
- RAW / RLE / DICT 的纹理表达。

当前视觉偏差的主要来源不是配色，而是：

1. 列块轨道使用多行换行模型，而目标是“一列一条水平轨道”。
2. 页面比例没有以效果图的视口为基准。
3. 底部执行区在 1366px 以下变成 2×2，目标图在约 1024px 宽仍是四栏。
4. 中心画布信息没有占满可用宽度，形成大面积无意义留白。
5. 列类型存在于 API 数据中，但没有进入轨道标签。
6. 标题、图例和工具栏允许换行，导致面板头部高度不稳定。

---

## 2. 固定验收视口

### 主验收视口

```text
Viewport: 1024 × 576
Device scale factor: 1
Browser zoom: 100%
```

必须在该视口下与效果图进行同尺寸截图比较。

### 次级视口

```text
Viewport: 1440 × 900
Device scale factor: 1
Browser zoom: 100%
```

不得拿 1745×873 的实现截图与 1024×576 的效果图直接判断比例。

---

## 3. 页面几何规格

### 1024×576 基准

| 区域 | 目标值 |
|---|---:|
| 顶部栏高度 | 44px |
| 底部状态栏高度 | 24px |
| 左侧功能轨道 | 56px |
| 数据结构面板 | 188–204px，默认 196px |
| 块检查器 | 208–232px，默认 220px |
| 分隔拖拽区 | 4px |
| 下方执行工作台 | 148–168px，默认 156px |
| 一级面板标题栏 | 30–32px |
| 面板描边 | 1px |
| 一级面板圆角 | 0–4px |
| 常驻阴影 | 禁止 |

### 1440×900 自适应

```text
rail: 56px
left panel: clamp(196px, 16vw, 232px)
right panel: clamp(220px, 19vw, 288px)
lower panel: clamp(156px, 23vh, 210px)
center panel: remaining width
```

用户拖拽调整仍然保留，但默认值必须先满足效果图比例。

---

## 4. 第一优先级：重构列块轨道模型

### 4.1 结构原则

每个字段只能占一条水平轨道：

```text
order_id  BIGINT       [01 RAW] [02 RAW] [03 RAW] ... [72 RAW]
region    VARCHAR      [01 DICT][02 DICT][03 RLE] ... [72 DICT]
amount    DECIMAL      [01 RAW] [02 RLE] [03 RLE] ... [72 RAW]
```

禁止把同一列的块按照 `blocksPerRow` 换成多行。

### 4.2 标签区

每条轨道左侧标签固定宽度：

```text
width: 88px
column name: 11px / 600 / mono
logical type: 9px / normal / mono / tertiary
```

不再显示“9 块”作为第二视觉层；块总数可以放在 tooltip、面板摘要或轨道尾部。

### 4.3 块窗口

对于块数较多的列，默认展示：

```text
前 N 个块 + 省略标记 + 最后一个块
```

1024px 下建议：

```text
N = 根据中心区宽度动态计算，通常为 7–9
```

示例：

```text
[01][02][03][04][05][06][07][08][…][72]
```

要求：

- 一条轨道不换行；
- 中心区宽度变化时重新计算可见块数；
- 已选中的块如果不在默认窗口内，应调整窗口使它可见；
- 可以保留横向滚动作为兜底，但默认画面不得出现空旷的大白区；
- 不改变块选择事件、键盘导航、裁剪状态和 Store 数据。

### 4.4 块尺寸

```text
height: 26px
width: 38–42px
gap: 3px
border-radius: 2px
```

块内信息：

```text
第一行：两位块编号，9px mono
第二行：RAW / RLE / DICT，8px mono
```

当前仅显示编码缩写不足以形成参考图的物理块感。

### 4.5 状态语法

编码类型主要依靠纹理，不依靠鲜艳颜色：

| 状态 | 表现 |
|---|---|
| RAW | 稀疏 45° 细斜线 |
| RLE | 水平重复短线 |
| DICT | 低对比度点阵 |
| skipped | 降低不透明度 + 更稀疏斜线，不覆盖编码识别 |
| scanned | 中等强度描边 |
| active | 2px 低饱和墨绿色描边 + 极浅强调底 |
| selected | 深灰内描边或 outline，与 active 可叠加 |
| cache hit | 可选 3px 实心角标，不使用新颜色 |

必须保证灰度打印后仍可区分 RAW / RLE / DICT / skipped / active。

---

## 5. 面板头部

`列块存储映射` 标题、编码图例和工具区必须处于同一行。

目标结构：

```text
[列块存储映射] [RAW] [RLE] [DICT] [跳过] [已扫描] [活动块]
                                                [显示 ▾] [密度 ▾] [6列·432块]
```

约束：

- 高度 32px；
- 禁止 `flex-wrap`；
- 图例可在窄屏隐藏文字、只保留纹理与 tooltip；
- 工具栏不得将面板头部撑成两行；
- 将“每行块数”改成“密度”或“可见块数”，不再控制轨道换行。

---

## 6. 底部执行工作台

内容结构已经正确，仍使用四个区域：

```text
执行轨迹 | 执行统计 | 筛选条件 | 运行状态
```

但在 1024px 宽时仍必须保持四栏，不得变成 2×2。

建议比例：

```css
grid-template-columns:
  minmax(260px, 1.45fr)
  minmax(150px, 0.8fr)
  minmax(170px, 0.95fr)
  minmax(150px, 0.8fr);
```

只有在 `< 900px` 时才允许降级为 2×2。

压缩规则：

- 标题栏 28px；
- 内容区 padding 7px 9px；
- 数据行 20–22px；
- 数字使用等宽字体并右对齐；
- 执行计划使用树线和等宽文本；
- 不添加卡片阴影。

---

## 7. 顶部栏和功能轨道

### 功能轨道

```text
width: 56px
icon area: 22px
label: 9–10px
selected: 左侧 2px 强调线 + 轻微背景变化
```

不要使用大面积胶囊选中背景。

### 顶部栏

1024px 下：

```text
brand: 168px
dataset selector: 142–160px
search: remaining width
actions: import + run
```

在空间不足时：

1. 先隐藏用户名；
2. 再将“退出”移入轻量菜单；
3. 不允许搜索框把操作按钮挤出画面。

---

## 8. Block Inspector

保留现有元数据、编码候选、最终选择和选择原因。

视觉调整：

- 面板标题固定为“块检查器”；
- 下一行显示 `Block 07 / region`；
- 编码名称作为主要值，但不做巨大营销式标题；
- 元数据使用 `64px + 1fr` 双列；
- 数值右对齐或使用 mono；
- 编码候选表的选中行使用极浅强调底和左侧 2px 标记；
- 选择原因用普通正文，不放进有阴影卡片；
- 区块之间使用 1px 分隔线而不是多个圆角卡片。

---

## 9. 本批次允许修改的文件

优先限制在：

```text
frontend/src/design-system/tokens.css
frontend/src/components/workspace/TopBar.vue
frontend/src/layouts/WorkspaceLayout.vue
frontend/src/stores/workspaceLayoutStore.ts
frontend/src/components/storage-map/StorageMapCanvas.vue
frontend/src/components/storage-map/ColumnTrack.vue
frontend/src/components/storage-map/BlockCell.vue
frontend/src/components/workspace/MapEncodingLegend.vue
frontend/src/components/block-inspector/BlockInspector.vue
frontend/src/components/block-inspector/CodecCandidateTable.vue
frontend/src/components/execution-plan/ExecutionWorkbench.vue
```

如确需新建纯展示组件，可以在以下目录新增：

```text
frontend/src/components/storage-map/
frontend/src/components/workspace/
```

---

## 10. 严格禁止

- 修改 API 请求或响应类型；
- 修改 Pinia Store 的业务行为；
- 删除拖拽调整、折叠、块选择或键盘导航；
- 引入新的 UI 框架；
- 加入渐变、玻璃拟态、大阴影、发光效果；
- 给每种编码配置一种鲜艳颜色；
- 把主页面拆成圆角卡片堆；
- 为追求截图相似度写死假数据；
- 只在 1440px 下调好，忽略 1024×576；
- 没有截图比较就声称“已还原”。

---

## 11. Codex 可直接执行的 Prompt

```text
你正在修改 VeyraDev/ColumnLab 仓库的 frontend。

任务：仅重构 Workspace / 存储映射主界面的视觉与布局，使其在
1024×576、DPR 1、100% zoom 下逼近已提供的目标效果图。

先阅读：
- frontend/src/design-system/tokens.css
- frontend/src/layouts/WorkspaceLayout.vue
- frontend/src/stores/workspaceLayoutStore.ts
- frontend/src/components/storage-map/StorageMapCanvas.vue
- frontend/src/components/storage-map/ColumnTrack.vue
- frontend/src/components/storage-map/BlockCell.vue
- frontend/src/components/block-inspector/BlockInspector.vue
- frontend/src/components/execution-plan/ExecutionWorkbench.vue

执行前先输出：
1. 将修改的文件；
2. 每个文件修改目的；
3. 明确不会修改的业务逻辑。

核心改动：
1. 把 ColumnTrack 从“按 blocksPerRow 换成多行”改为“一列一条水平轨道”。
2. 每条轨道展示列名、logical_type、块窗口。
3. 块窗口采用“前 N 个 + 省略 + 最后一个”，N 根据可用宽度计算。
4. 块尺寸约 40×26px，块内同时显示编号和编码缩写。
5. 保留 RAW / RLE / DICT 纹理以及 selected / active / scanned /
   skipped / to_read 状态。
6. 面板标题、图例、工具栏必须单行，禁止 flex-wrap。
7. 默认布局：rail 56px，left 196px，right 220px，lower 156px。
8. ExecutionWorkbench 在 1024px 仍保持四栏；仅小于 900px 时改 2×2。
9. 保留现有 API、Store、事件、拖拽、折叠和键盘导航。
10. 不使用渐变按钮、玻璃拟态、大阴影、巨大圆角或彩虹编码色。

验证：
- npm run build
- 使用 Playwright 截取 1024×576 和 1440×900 两张截图
- 输出修改前后截图路径
- 按 Geometry / Density / Hierarchy / Surface / State
  五个维度说明仍存在的偏差
- 不得仅描述“更美观”，必须报告具体尺寸与状态覆盖情况
```

---

## 12. 验收清单

### Geometry

- [ ] 1024×576 下所有主区域完整可见。
- [ ] 功能轨道 56px 左右。
- [ ] 左侧数据结构约 196px。
- [ ] 右侧检查器约 220px。
- [ ] 底部执行区约 156px。
- [ ] 中间轨道不发生列内换行。
- [ ] 无大面积无意义空白。

### Density

- [ ] 面板标题栏不超过 32px。
- [ ] 轨道行高不超过 32px。
- [ ] 底部四栏在 1024px 下保持一行。
- [ ] 信息密度接近工程仪器而非普通后台。

### Hierarchy

- [ ] 列块物理结构是第一视觉中心。
- [ ] 编码候选与选择依据清晰但不喧宾夺主。
- [ ] 主操作每屏最多一个实心按钮。
- [ ] 没有统计卡片堆。

### Surface

- [ ] 主页面靠边框和底色分区。
- [ ] 无常驻阴影。
- [ ] 圆角不超过 4px。
- [ ] 90% 以上为中性色。

### State

- [ ] RAW / RLE / DICT 灰度下可区分。
- [ ] selected / active / scanned / skipped 可同时表达。
- [ ] 跳过状态不会完全覆盖原编码纹理。
- [ ] Focus Ring 和键盘导航仍可用。

---

## 13. 后续批次

Batch 1 验收通过后再处理：

- Batch 2：抽取统一的 Observatory App Shell。
- Batch 3：为导入页生成并确认静态高保真图片，再落地双栏导入工作台。
- Batch 4：为查询页生成并确认静态高保真图片，再落地 SQL / Plan / Result / Profile 工作台。
- Batch 5：压缩实验与性能实验统一为科学实验台 Pattern。
- Batch 6：同视口视觉回归、响应式与可访问性 QA。
