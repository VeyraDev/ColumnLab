# ColumnLab UI 视觉重构任务包 · Batch 2
## 1918×952 视觉基线重构

---

## 0. 重要修正

主验收视口改为：

```text
Viewport: 1918 × 952
Device scale factor: 1
Browser zoom: 100%
```

1024×576 的效果图只作为以下内容的参考：

- 区域比例；
- 信息层级；
- 视觉密度；
- 组件语法；
- 间距与边界关系。

禁止再将效果图中的绝对像素直接复制到 1918×952 的运行界面。

---

## 1. 当前问题的根因

当前界面不是单纯“字号太小”或“颜色太灰”，而是整套尺寸模型仍按小型紧凑 IDE 构建：

```text
TopBar: 44px
Control: 26px
Left panel: 196px
Right panel: 220px
Block: 40×26px
Track row: 32px
Lower panel: 160px
Panel gap: 0
```

这些值在 1918×952 下会同时造成：

- 顶部组件拥挤；
- 两侧面板内容被压缩；
- 中央块过小；
- 中央剩余区域空荡；
- 底部信息贴边；
- 字体和纹理互相干扰；
- 页面像基础后台或低配 IDE，而不是观测仪器。

本轮禁止继续零散调整某一个组件。必须统一重定：

1. 页面比例；
2. 空间节奏；
3. 字体层级；
4. 核心组件尺寸；
5. 信息展示顺序。

---

# 2. 1918×952 页面几何基线

## 2.1 总体结构

```text
┌──────────────────────────────────────────────────────────────┐
│ TopBar                                                       │
├──────┬──────────────┬────────────────────────┬───────────────┤
│ Rail │ Data Schema  │ Storage Map            │ Inspector     │
│      │              │                        │               │
├──────┴──────────────┴────────────────────────┴───────────────┤
│ Execution Trace │ Stats │ Filter │ Run Status               │
├──────────────────────────────────────────────────────────────┤
│ Status Bar                                                   │
└──────────────────────────────────────────────────────────────┘
```

## 2.2 推荐尺寸

```text
Viewport                         1918 × 952
Outer workspace padding          8px
Primary panel gap                8px
TopBar height                    56px
StatusBar height                 26px
Function rail width              64px
Left panel default width         300px
Right panel default width        340px
Lower workbench default height   220px
Splitter visual width            4px
```

主体可用宽度约：

```text
1918
- 16 outer padding
- 64 rail
- 300 left
- 340 right
- 24 gaps
≈ 1174px center workspace
```

中央区不再占据几乎全部宽度，也不允许左右面板窄到只能显示省略号。

## 2.3 自适应范围

```text
left panel:
  min 260px
  default 300px
  max 380px

right panel:
  min 300px
  default 340px
  max 440px

lower workbench:
  min 190px
  default 220px
  max 320px
```

拖拽行为保留，但默认比例必须先成立。

---

# 3. 页面表面与“呼吸感”

## 3.1 不再使用全贴边分割

当前页面所有区域通过连续边框拼接，视觉上像表格网格。

改为：

```text
workspace background: 统一浅灰底
panel background: 接近纸白
panel border: 1px
panel radius: 4–5px
panel shadow: none
panel gap: 8px
```

应用范围：

- 数据结构；
- 列块存储映射；
- 块检查器；
- 执行轨迹；
- 执行统计；
- 筛选条件；
- 运行状态。

禁止：

- 16px 以上大间距；
- 大圆角；
- 卡片阴影；
- 每个字段再套小卡片；
- 玻璃拟态。

目标是：

```text
宽松但不空荡；
有边界但不拥挤；
有呼吸感但仍保持工程信息密度。
```

---

# 4. 字体与颜色重新分工

## 4.1 核心原则

**信息载体默认使用近黑色。**

灰色只用于：

- 搜索框 placeholder；
- disabled 控件；
- 空状态提示；
- 非关键帮助文本；
- 次要时间戳；
- 不需要第一眼读取的辅助说明。

禁止再通过大面积灰字表达“高级感”。

## 4.2 Token 建议

```css
--text-primary: #1d1f1b;
--text-body: #282b26;
--text-secondary: #4e534b;
--text-muted: #7f847b;
--text-disabled: #a4a8a0;
```

用途：

| 内容 | 颜色 |
|---|---|
| 面板标题 | `text-primary` |
| 表格正文 | `text-primary` |
| 数值 | `text-primary` |
| 字段类型 | `text-body` |
| 编码方式 | `text-primary` |
| 元数据标签 | `text-secondary` |
| placeholder | `text-muted` |
| disabled | `text-disabled` |

## 4.3 字号

```text
Global body                  14px
Brand title                  17px / 600
Panel title                  14px / 600
Section title                13px / 600
Table body                   13px
Metadata label               12px
Metadata value               13px
Block number                 10px
Block encoding               9px
Status/helper                11–12px
```

不要靠灰度建立所有层级，优先使用：

- 字重；
- 字号；
- 间距；
- 对齐；
- 分隔线。

---

# 5. TopBar 重构

## 5.1 当前问题

当前顶栏：

- 高度太低；
- 数据集选择器太窄；
- 搜索框过长；
- 操作按钮贴得过近；
- 用户名与退出按钮进一步挤压主操作；
- 所有控件只有 26px 高。

## 5.2 目标规格

```text
TopBar height         56px
Inner horizontal pad  14px
Control height        34px
Control gap           10–12px
```

布局：

```text
Brand         220px
Dataset       280–320px
Search        min 420px, max 760px, flex
Spacer        flex
Import        92px
Run           106px
User menu     40px
```

推荐结构：

```text
ColumnLab
列式存储引擎观测台

[ Sample - Superstore (9,994 行) ▼ ]
[ 搜索表、列或过滤条件 (Ctrl+K)              ]
[ 导入数据 ] [ ▶ 运行查询 ] [ 用户菜单 ]
```

规则：

- “运行查询”是本屏唯一实心按钮；
- “导入数据”为描边按钮；
- 用户名不直接占据主操作行，移入菜单；
- 退出不作为顶栏常驻大按钮；
- 搜索框不能无限扩张；
- 按钮文字使用黑色或白色高对比，不使用浅灰。

---

# 6. 中央列块存储映射

## 6.1 轨道尺寸

当前 40×26px 块不适用于 1918×952。

改为：

```text
Track row height       48px
Track label width      126px
Block width            54px
Block height           34px
Block gap              4px
Track horizontal pad   10px
```

每一列仍保持一条水平轨道。

## 6.2 行分隔

效果图中每一列轨道之间存在清晰但低对比的细线。

增加：

```css
.column-track {
  border-bottom: 1px solid var(--border-subtle);
}
```

每行：

```text
padding: 6px 0
```

最后一行可以去除 border。

目标：

- 行之间可快速扫读；
- 列标签与块保持基线对齐；
- 不再像一堆漂浮的小按钮。

## 6.3 块内部可读性

当前文字和纹理混在一起。

使用三层结构：

```text
block background base
pattern pseudo-element with low opacity
text layer above pattern
```

建议：

```css
.block-cell::before {
  opacity: 0.22–0.30;
}

.cell-id,
.cell-enc {
  position: relative;
  z-index: 1;
  color: var(--text-primary);
}
```

纹理规则：

| 编码 | 纹理 |
|---|---|
| RAW | 稀疏 45° 斜线，间隔 6px |
| RLE | 水平细线，间隔 5px |
| DICT | 点阵，间隔 6px |
| skipped | 整体降低透明度 + 删除线/遮罩 |
| active | 2px 墨绿色边框 |
| scanned | 1px 中深灰边框 |

禁止让纹理线穿过文字形成视觉噪声。

可选方案：

```text
上半区显示编号；
下半区显示编码和较弱纹理。
```

## 6.4 块窗口

自动密度按实际中心宽度计算。

1918×952 下，默认中心区域应展示约：

```text
14–18 个首块 + 省略 + 最后块
```

不能仍只显示 8–9 个块后留下巨大空白。

## 6.5 面板标题栏

标题栏改为 40px 左右，不再挤成一条细线。

布局：

```text
列块存储映射   RAW RLE DICT 跳过 已扫描 活动块
                                      显示 [逻辑行范围] 密度 [自动]
```

要求：

- 标题 14px / 600 / 黑色；
- 图例文字 12px；
- 工具区 12px；
- 保持单行；
- 左右各 12px padding。

---

# 7. 左侧数据结构面板

## 7.1 信息结构

改为：

```text
数据结构
────────────────
sales_2026                         6 列
────────────────
列名              类型          块数
order_id          BIGINT          72
region            VARCHAR         72
...
```

不要在面板标题中重复顶部数据集名称。

## 7.2 表格视觉

```text
Panel inner padding       8px
Object header height      36px
Table header height       32px
Table row height          34px
Cell horizontal padding   10px
```

列宽：

```text
name    minmax(0, 1fr)
type    92px
count   48px
```

规则：

- 表格不要左贴边、右贴边；
- 内容区域与面板边缘至少 8px；
- 列名、类型、块数全部使用深色；
- 类型无需大写浅灰；
- 数字右对齐；
- 表头可使用较浅底色，但文字必须清楚；
- 行 hover 只改变极轻背景；
- 不使用彩色圆点。

---

# 8. 右侧块检查器彻底重排

## 8.1 当前问题

当前使用：

```text
大编码标题
压缩进度线
候选表
Tab：元数据 / 编码结构 / 裁剪依据
```

结果是：

- 核心信息被 Tab 隐藏；
- 用户第一眼不知道每个数字代表什么；
- 页面重点变成了一个大写 RLE；
- 没有清楚回答“为什么选择该编码”。

## 8.2 目标信息顺序

块检查器必须按以下固定顺序从上到下展示：

### A. 对象身份

```text
Block 07 / region
```

### B. 核心元数据

```text
编码方式          DICTIONARY
起始行            6,144
行数              1,024
原始大小          63.8 KiB
压缩后大小        18.4 KiB
压缩率            71.2%
min               "Africa"
max               "West"
distinct_count    12
null_count        0
CRC32             0x9B4A1C2F
```

采用双列 definition list：

```text
label  112px
value  remaining
row    24px
```

标签用中深灰，值用黑色，数字右对齐或 mono。

### C. 编码竞争

```text
编码候选                         估算大小

RAW                              63.8 KiB
RLE                              46.2 KiB
DICTIONARY                       18.4 KiB
```

被选中行：

- 极浅强调底；
- 左侧 2px 强调线；
- 黑色粗体；
- 不使用进度条。

### D. 最终选择

```text
最终选择          DICTIONARY
编码宽度          uint8
字典项            17
选择依据          实际大小最小，收益超过 5%
```

最终选择是系统核心结论，必须直接展示，不能藏在 Tab 内。

## 8.3 不再使用 Tab 隐藏主信息

以下内容可以作为折叠详情：

- RLE 游程明细；
- 字典条目；
- packed codes；
- 完整裁剪日志。

但核心元数据、候选大小和最终选择必须始终可见。

## 8.4 默认宽度

```text
Right inspector default width: 340px
```

当内容较多时垂直滚动，禁止横向滚动。

---

# 9. 底部执行工作台

## 9.1 区域尺寸

```text
Default height          220px
Outer padding           8px
Card gap                8px
```

四个独立面板：

```text
执行轨迹    1.45fr
执行统计    0.8fr
筛选条件    0.9fr
运行状态    0.8fr
```

不再通过连续竖线拼成一张大表。

## 9.2 卡片规格

```text
background      panel
border          1px
radius          4px
shadow          none
header height   34px
body padding    10–12px
```

## 9.3 内容排版

执行轨迹：

- 等宽字体；
- 行高 20px；
- 左侧至少 12px padding；
- 计划树文字黑色；
- 辅助数字可以中灰。

执行统计：

```text
扫描块      14 / 72
跳过块      58
解码块      2
读取量      1.8 MiB
耗时        21.7 ms
```

标签和数值都清楚可见，数值右对齐。

筛选条件：

- SQL 使用等宽字体；
- 黑色；
- 行高 1.55；
- WHERE / AND / GROUP BY 可加字重，不使用彩虹语法色。

运行状态：

```text
● 已完成
开始时间    2025-05-19 14:28:31
结束时间    2025-05-19 14:28:31
查询耗时    21.7 ms
线程数      4
```

---

# 10. 全局默认宽度与持久化

当前 localStorage 会保留旧的 196px / 220px / 160px 布局。

更新默认尺寸后，旧用户仍可能继续读取旧值。

必须增加 layout schema version：

```ts
const LAYOUT_VERSION = 2
```

持久化：

```ts
{
  version: 2,
  leftWidth: 300,
  rightWidth: 340,
  lowerHeightPx: 220,
  ...
}
```

如果读取到：

- 无 version；
- version < 2；
- 明显属于旧尺寸的默认值；

则迁移为新基线。

否则代码改了默认值，现有浏览器仍会显示旧布局。

---

# 11. 允许修改的文件

```text
frontend/src/design-system/tokens.css
frontend/src/layouts/WorkspaceLayout.vue
frontend/src/stores/workspaceLayoutStore.ts
frontend/src/components/workspace/TopBar.vue
frontend/src/components/workspace/FunctionRail.vue
frontend/src/components/workspace/DataStructurePanel.vue
frontend/src/components/storage-map/StorageMapCanvas.vue
frontend/src/components/storage-map/ColumnTrack.vue
frontend/src/components/storage-map/BlockCell.vue
frontend/src/components/storage-map/blockWindow.ts
frontend/src/components/block-inspector/BlockInspector.vue
frontend/src/components/execution-plan/ExecutionWorkbench.vue
```

可新建纯展示组件：

```text
BlockMetadataGrid.vue
CodecCompetitionTable.vue
FinalCodecDecision.vue
```

---

# 12. 禁止事项

- 不得继续以 1024×576 作为主尺寸；
- 不得只放大中央块而不重调左右面板；
- 不得靠大量浅灰字制造层级；
- 不得保留核心信息 Tab 隐藏结构；
- 不得将所有面板继续无间距拼接；
- 不得加入阴影、渐变、大圆角；
- 不得给每种编码配置彩色背景；
- 不得使用假数据替换真实业务数据；
- 不得修改 API 语义和查询逻辑；
- 不得删除拖拽、折叠、键盘导航。

---

# 13. 可直接交给 Codex 的 Prompt

```text
重构 VeyraDev/ColumnLab frontend 的 Workspace 视觉基线。

主视口是 1918×952，浏览器缩放 100%。1024×576 效果图仅作为比例、
信息层级和视觉语法参考，不复制其绝对像素。

这不是局部修补，请统一修改 TopBar、Workspace Layout、DataStructure、
StorageMap、BlockInspector、ExecutionWorkbench 和 Design Tokens。

必须完成：

1. 新页面基线：
   - TopBar 56px
   - rail 64px
   - left default 300px
   - right default 340px
   - lower default 220px
   - workspace outer padding 8px
   - primary panel gap 8px

2. 增加 layout storage version，迁移旧的 196/220/160 默认布局，
   防止 localStorage 继续覆盖新尺寸。

3. TopBar：
   - 控件 34px 高
   - brand 220px
   - dataset 280–320px
   - search max 760px
   - 用户名和退出移入用户菜单
   - 运行查询为唯一实心按钮
   - 整体不拥挤

4. 字体：
   - 全局 14px
   - 信息载体默认近黑色
   - 只有 placeholder、disabled、空状态和辅助说明使用灰色
   - 面板标题 14px/600
   - 表格和数值不得使用浅灰

5. Storage Map：
   - track row 48px
   - label width 126px
   - block 54×34px
   - gap 4px
   - 每行增加 1px 细分隔线
   - 纹理放在低透明度 pseudo-element
   - 文字位于纹理上层，必须清晰
   - 1918px 下自动显示约 14–18 个首块，不留巨大空白

6. DataStructure：
   - 标题固定为“数据结构”
   - 增加表对象行：table name + column count
   - 表格内部左右各至少 8px
   - 行高 34px
   - 列名/类型/块数全部清楚可读
   - 默认宽度 300px

7. BlockInspector：
   - 默认宽度 340px
   - 移除依赖 Tab 才能查看核心信息的结构
   - 固定顺序：
     Block/字段
     → 编码方式、起始行、行数、原始大小、压缩大小、压缩率、
       min、max、distinct、null、CRC32
     → RAW/RLE/DICT 大小比较
     → 最终选择、编码参数、选择依据
   - 候选选择行用浅底+左侧 2px 标记
   - 不使用候选进度条
   - 不允许横向滚动

8. ExecutionWorkbench：
   - 默认高度 220px
   - 外层 padding 8px
   - 四张卡片 gap 8px
   - 每张卡片独立 border + 4px radius
   - body padding 10–12px
   - 所有主要文字黑色
   - 数值右对齐

9. 保留现有 API、Pinia、拖拽、折叠、选择、键盘导航和查询逻辑。

验收截图：
- 1918×952 idle
- 1918×952 completed
- 1918×952 active + skipped
- 1918×952 inspector with DICTIONARY selected

执行后按 Geometry / Density / Hierarchy / Surface / Typography / State
报告偏差。不得只说“更美观”。
```

---

# 14. 验收标准

## Geometry

- [ ] 顶栏不拥挤，控件高度明显提升。
- [ ] 左栏默认约 300px。
- [ ] 右栏默认约 340px。
- [ ] 中央区仍是最大区域，但不产生大面积无意义空白。
- [ ] 底部默认约 220px。
- [ ] 一级面板之间存在 8px 左右间距。

## Typography

- [ ] 表格正文、元数据、编码和数值均为黑色或近黑色。
- [ ] 灰色仅用于 placeholder、disabled、空状态与辅助说明。
- [ ] 重要标题使用 600 字重。
- [ ] 不再出现“所有文字都灰”的视觉状态。

## Storage Map

- [ ] 块大小约 54×34px。
- [ ] 块编号和编码清晰，不与纹理混合。
- [ ] 每条列轨道存在细分隔线。
- [ ] 1918px 下显示 14–18 个首块。
- [ ] RAW/RLE/DICT 灰度下仍可区分。

## Left Panel

- [ ] 显示数据结构 → 表 → 列三级关系。
- [ ] 表格不贴面板左右边缘。
- [ ] 类型和块数无需拖宽即可读取。

## Inspector

- [ ] 第一眼能回答“这是哪个块、什么字段、选择了什么编码”。
- [ ] 核心元数据全部直接可见。
- [ ] 三种编码大小比较直接可见。
- [ ] 最终选择和选择依据直接可见。
- [ ] 不需要切换 Tab 才能理解核心结论。

## Lower Workbench

- [ ] 四个区域是有间距的独立卡片。
- [ ] 内容不贴边。
- [ ] 计划树、统计、条件和状态均清楚可读。
- [ ] 宽松但不空荡。
