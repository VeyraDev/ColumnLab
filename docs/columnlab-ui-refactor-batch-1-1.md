# ColumnLab UI 视觉重构任务包 · Batch 1.1

## 结论

Batch 1 的方向正确，但尚未通过视觉验收。

已经完成：

- 一列一条水平轨道；
- 列名与逻辑类型进入核心画面；
- 前 N 个块 + 省略 + 末块；
- 块内同时显示编号和编码；
- 下方执行区保持四栏；
- 右侧出现编码候选和元数据。

本轮不重做结构，只修复验收环境、空间利用率和局部溢出。

---

## 1. 先固定视觉验收环境

当前提交的截图为 1918×958，不能与 1024×576 的目标图直接比较。

必须增加或修正 Playwright 截图用例：

```ts
test.use({
  viewport: { width: 1024, height: 576 },
  deviceScaleFactor: 1,
})
```

同时输出：

```text
workspace-1024x576.png
workspace-1440x900.png
```

截图前必须：

1. 等待数据加载完成；
2. 等待字体和布局稳定；
3. 使用成功执行的查询状态；
4. 关闭开发工具；
5. 浏览器缩放为 100%；
6. 不裁剪页面，只截取 viewport。

视觉验收截图不得使用“查询失败”状态替代目标图中的“已完成”状态。

---

## 2. 使用可比较的数据状态

当前截图为：

```text
21 列
2121 块
查询失败
```

目标图为较小的代表性数据集和已完成查询。

不要求生产代码伪造数据，但视觉回归测试必须使用稳定 fixture：

```text
6–8 列
每列约 72 块
同时包含 RAW / RLE / DICTIONARY
至少有 skipped / scanned / active 状态
查询状态 completed
底部有物理计划、统计、过滤条件和运行元数据
```

可以通过：

- 测试数据库 seed；
- Playwright API mock；
- 已存在的固定演示数据集；

实现，但禁止在组件内写死假数据。

---

## 3. P0：中心画布必须利用可用宽度

当前在 1918px 宽度下只显示 8 个首块、一个省略号和末块，轨道右侧仍有大量空白。

要求使用 `ResizeObserver` 根据轨道容器宽度动态计算 `visibleCount`。

建议计算：

```text
available =
  containerWidth
  - labelWidth
  - labelGap
  - lastBlockWidth
  - ellipsisWidth
  - horizontalPadding

visibleCount =
  floor((available + gap) / (blockWidth + gap))
```

约束：

- 1024px 视口通常显示 7–9 个首块；
- 1440px 显示更多；
- 1918px 不应仍固定显示 8 个；
- 正常数据下，最后一个可见块之后的无意义空白不得超过轨道区域宽度的 20%；
- 若所有块能够完整放下，则不显示省略号；
- 选中中间块时，窗口必须移动，使选中块可见；
- 保留末块作为物理范围终点。

不要通过拉宽每个块来填满空间；优先增加可见块数量。

---

## 4. P0：压缩底部执行区的重复头部

当前展开状态存在两层标题：

```text
▼ 执行计划
执行轨迹（物理执行计划）
```

第一层占用了过多垂直空间。

调整为：

```text
4–8px splitter / drag handle
执行轨迹 | 执行统计 | 筛选条件 | 运行状态
```

折叠按钮要求：

- 放在 splitter 中央；
- 只显示小型 chevron；
- 用 tooltip 表达“收起/展开执行区”；
- 展开时不再显示大号“执行计划”文字条。

1024×576 下：

```text
底部工作台总高度：150–164px
splitter：不超过 8px
pane header：26–28px
```

---

## 5. P0：消除 Block Inspector 横向滚动

当前右侧面板底部出现横向滚动条，编码候选选中行文字也发生截断。

必须做到：

```css
.block-inspector,
.panel-body,
.candidate-table {
  min-width: 0;
  overflow-x: hidden;
}
```

编码候选表改成稳定三列：

```text
编码       大小       差异/状态
RAW        723 B      基准
RLE        815 B      +12.7%
DICT       809 B      +11.9%
```

要求：

- 编码列固定宽度；
- 大小列右对齐，使用等宽数字；
- 状态列可压缩；
- “SELECTED”不得作为溢出的第四列文字；
- 选中态使用左侧 2px 标记和极浅底色；
- 删除候选行中装饰性短进度条，避免像普通 Dashboard 图表；
- 面板内部任何宽度下都不得出现横向滚动条。

---

## 6. P1：左侧数据结构改为单行表格

当前真实列名会自动折成两行，例如：

```text
Order
Date
```

目标是工程表格，而不是自动换行的卡片列表。

三列结构：

```text
列名                 类型       块数
Customer Name        VARCHAR    101
```

约束：

```css
column name:
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;

type:
  white-space: nowrap;

block count:
  text-align: right;
  font-variant-numeric: tabular-nums;
```

列宽建议：

```text
name: minmax(0, 1fr)
type: 68–76px
count: 34–40px
```

鼠标悬停通过 `title` 或 tooltip 显示完整列名。

---

## 7. P1：恢复物理行号标尺

目标图底部有与块轨道对齐的行范围标尺。

当前只有：

```text
catalog · 9,994 行 · 方向键移动选中块
```

请在轨道底部增加真正的 row axis：

```text
逻辑行号  0 ───── 1,024 ───── 2,048 ... 73,728
```

要求：

- 起点与第一个块左边缘对齐；
- 终点与末块右边缘对应；
- 使用细线、刻度和 9–10px 等宽数字；
- 不使用图表库；
- footer 只保留数据来源与操作提示；
- 标尺属于存储映射内容，不属于状态栏。

---

## 8. P1：调整表面层级，而不是重新配色

当前配色方向正确，不更换主题。

只做以下微调：

- `border-default` 比当前提高一个轻微对比等级；
- 面板标题栏与内容底色形成非常轻微的明度差；
- 主工作区底板可略深于面板；
- 不新增阴影；
- 不新增渐变；
- 不新增彩色图标背景；
- 强调色仍只用于 active、running 和关键选择。

---

## 9. P1：滚动条降噪

当前中心区和右侧滚动条视觉重量过高。

使用轻量滚动条：

```css
* {
  scrollbar-width: thin;
  scrollbar-color: var(--scroll-thumb) transparent;
}
```

WebKit 同步处理：

```text
宽度 6–8px
默认低对比度
hover 时才加深
轨道透明
```

不能完全隐藏滚动条，因为它仍要表达可滚动性。

---

## 10. 状态覆盖截图

本轮必须额外输出四张局部或全页截图：

```text
01-idle.png
02-query-completed.png
03-block-active-and-skipped.png
04-query-failed.png
```

其中 `02-query-completed.png` 才用于和目标图进行主视觉比较。

必须验证：

- RAW / RLE / DICT；
- selected；
- active；
- scanned；
- skipped；
- 查询成功；
- 查询失败。

---

## 11. 可直接交给 Codex 的 Prompt

```text
继续修改 ColumnLab frontend，仅完成 Workspace Batch 1.1，不处理其他页面。

当前 Batch 1 已完成单行列轨道，但视觉验收仍存在以下问题：

1. 当前截图为 1918×958，必须新增 1024×576 和 1440×900 的 Playwright
   固定视口截图。
2. 主验收截图必须使用 completed 查询状态和稳定演示数据，不能使用 failed 状态。
3. 列块窗口不能固定只显示 8 个首块。使用 ResizeObserver 按容器宽度动态
   计算 visibleCount。宽屏应显示更多块，轨道空白不得超过可用宽度 20%。
4. 移除展开状态下占高过大的“▼ 执行计划”文字条，只保留不超过 8px 的
   splitter 和小型折叠 chevron。
5. BlockInspector 不得出现横向滚动。编码候选表改为编码/大小/差异三列，
   数值右对齐，选中行使用左侧细标记，删除装饰性进度条。
6. 左侧列名禁止换行，使用 ellipsis；恢复列名/类型/块数三列。
7. 在列块轨道底部恢复与块位置对齐的逻辑行号标尺。
8. 只提高极轻微边框对比，不更换现有低饱和配色，不添加阴影、渐变、
   大圆角或彩色图标底。
9. 将滚动条收窄至 6–8px，并降低默认对比度。
10. 保留所有 API、Pinia、块选择、键盘导航、拖拽和折叠行为。

执行前先列出将修改的文件和原因。
执行后运行 npm run build 和 Playwright。
输出：
- workspace-1024x576.png
- workspace-1440x900.png
- idle / completed / active+skipped / failed 四种状态截图
- 仍存在的 Geometry / Density / Hierarchy / Surface / State 偏差

没有 1024×576 的 completed 截图，不得宣称本批次验收通过。
```

---

## 12. 通过标准

- [ ] 主验收截图尺寸严格为 1024×576。
- [ ] 使用 completed 查询状态。
- [ ] 中心轨道随宽度增加可见块，不再固定 8 个。
- [ ] 中心区无超过 20% 的无意义空白。
- [ ] 底部无重复“执行计划”大标题条。
- [ ] 右侧无横向滚动。
- [ ] 左侧列名不换行，块数可见。
- [ ] 行号标尺恢复。
- [ ] 四栏在 1024px 下完整可读。
- [ ] active / scanned / skipped 状态均有截图证明。
