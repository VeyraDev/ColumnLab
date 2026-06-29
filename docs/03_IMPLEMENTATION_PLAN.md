# ColumnLab 分阶段实施与验收计划

> 文档编号：CL-PLAN-001  
> 执行方式：每阶段形成独立、可运行、可测试的提交。禁止同时铺开全部页面后再补核心算法。

---

## 0. 执行总原则

1. 先引擎、后界面联调，但第一阶段同时搭建视觉骨架，避免最终套模板。
2. 每个阶段都必须有自动化测试和可观察交付物。
3. 不允许“先用 Pandas 跑通，后面再替换”作为正式主链路。
4. 不允许用 mock 数据长期支撑前端；API 未完成时 mock 仅限 Storybook/组件开发，并须明确隔离。
5. 每阶段未通过验收不得进入下一阶段。
6. 复杂度优先投入：文件格式、编码、查询、可靠性、可观测性。
7. 每个 PR 控制在可审查范围，避免一次性生成整个系统。

---

# Stage 0：新仓库与基础设施

## 目标

建立独立 ColumnLab 仓库，完成 RetailInsight 白名单移植和新视觉骨架。

## 后端任务

- 新建 Python 3.11+ 项目。
- 移植并重命名：
  - 配置；
  - SQLAlchemy Session；
  - JWT 与密码哈希；
  - 用户模型和认证接口；
  - 统一响应与异常处理。
- 删除所有 `retailinsight`、`ri_` 命名。
- 建立 Alembic 或等效迁移。
- 配置测试数据库。
- 建立结构化日志基础。

## 前端任务

- 移植 Vue/Vite/TypeScript/Pinia/Axios 基础。
- 创建新 router。
- 创建核心工作区空骨架：
  - 顶部栏；
  - 功能轨道；
  - 左中右面板；
  - 底部执行区；
  - 状态栏。
- 建立 design token。
- 覆盖 Element Plus 默认主题。
- 禁止复制 RetailInsight MainLayout 和 theme.css。

## 交付物

- 登录、注册、退出可用。
- 登录后显示与参考图结构一致的空工作区。
- 后端健康检查。
- 数据库迁移可执行。

## 验收

- 全仓搜索无 `RetailInsight`、`ri-`、黄绿主题变量。
- 1600×900 和 1366×768 均不溢出。
- 页面没有统计卡片、渐变、大圆角和常驻阴影。
- 后端测试可运行。
- 前端 build 通过。

---

# Stage 1：类型系统、向量与 Codec 基础

## 目标

建立不依赖 Web 框架的核心数据表示。

## 任务

- 实现 LogicalType。
- 实现 ValueVector、NullBitmap、SelectionVector。
- 实现 typed value serialization。
- 实现 Codec Protocol。
- 实现 RawCodec：
  - 固定宽度；
  - BOOLEAN bit packing；
  - UTF8 offsets/blob；
  - DATE/TIMESTAMP；
  - DECIMAL scale。
- 编写属性测试。

## 交付物

- `engine/types.py`
- `engine/vectors.py`
- `engine/codecs/raw.py`
- 单元与属性测试。

## 验收

- 所有类型 round-trip。
- Unicode、空字符串、NULL、极值通过。
- 不使用 Pickle。
- 编码结果是 bytes。
- 1000 组随机属性测试通过。

---

# Stage 2：RLE、Dictionary 与编码选择器

## 目标

完成任务书核心压缩算法，并提供压缩态能力。

## 任务

### RLE

- 生成 run；
- varint run length；
- NULL 打断规则；
- decode；
- equality/range filter；
- COUNT/SUM/MIN/MAX/AVG partial。

### Dictionary

- 字典构建；
- 稳定 code；
- bit width；
- packed codes；
- decode；
- equality/IN；
- dictionary negative check；
- GROUP BY code；
- COUNT/MIN/MAX 能力。

### Selector

- 为每块实际执行 RAW/RLE/DICT；
- 保存字节数与耗时；
- min gain；
- tie threshold；
- deterministic selection。

## 前端组件

独立开发：

- 编码纹理图例；
- CodecCandidateTable；
- RLE 摘要预览；
- Dictionary 摘要预览。

先使用测试夹具，不接生产 mock API。

## 验收

- `decode(encode(x)) == x`。
- RLE 算子不调用完整 decode。
- Dictionary codes 实际 bit packing。
- 长游程合成数据选择 RLE。
- 低基数随机数据选择 Dictionary。
- 高基数数据可回退 RAW。
- 候选比较结果可序列化为 API DTO。

---

# Stage 3：共享行组与列文件格式

## 目标

完成真实二进制列文件读写。

## 任务

- 实现 RowGroupBuilder。
- 字节预算估算。
- min/max/NULL/distinct 统计。
- FileHeader、BlockHeader、Index、Footer。
- ColumnWriter seek/write/finalize。
- ColumnReader footer-first open。
- CRC32。
- atomic temp file → final rename。
- golden test。
- 文件格式说明同步更新。

## 前端组件

- ColumnTrack；
- BlockCell；
- BlockInspector 静态结构；
- 大块数量 windowing。

## 验收

- 文件不是 JSON/CSV/Pickle。
- 多列行组 `row_start/row_count` 一致。
- Reader 可只加载 index 而不读 payload。
- 随机块读取正确。
- 篡改 payload 可触发 CRC 错误。
- 截断文件被拒绝。
- 未知版本被拒绝。
- 参考图中的列块映射可由真实测试文件渲染。

---

# Stage 4：Catalog、流式上传与导入任务

## 目标

完成从用户文件到可查询列式版本的完整导入。

## 任务

- 设计 Dataset、Version、Table、Column、BlockCatalog、ImportJob。
- 流式上传临时文件和 SHA-256。
- CSV incremental parser。
- XLSX read-only parser。
- 类型推断与全量验证。
- strict/coerce 模式。
- ImportCoordinator。
- staging、validate、atomic commit。
- SSE 事件。
- 取消任务。
- 导入恢复策略：首期失败后重启，不要求断点续写。

## 前端

- 导入页面；
- 阶段进度；
- 真实处理行数/字节；
- schema override；
- 错误样本；
- 完成后跳转 workspace。

## 验收

- 上传过程不一次性读完整文件。
- 大于内存安全阈值的 CSV 可导入。
- 中途失败没有可见半成品。
- 取消任务清理 staging。
- 全部列总行数一致。
- SSE 断线可通过查询任务状态恢复。
- 前端无假进度。

---

# Stage 5：SQL AST 与逻辑计划

## 目标

完成 SQL 子集的解析、校验和逻辑计划。

## 任务

- 集成 sqlglot。
- AST 转内部表达式。
- 类型检查。
- 列/表解析。
- 逻辑节点。
- Explain DTO。
- 不支持语法错误。
- 查询记录模型。

## 前端

- SQL 编辑器；
- 语法错误行提示；
- 逻辑计划树；
- 查询历史基础。

## 验收

- 支持规定 SQL 子集。
- JOIN、子查询、窗口函数返回明确“不支持”。
- 不将 SQL 交给 SQLite/DuckDB 执行。
- 同一 SQL 生成确定逻辑计划。
- 错误包含位置和原因。

---

# Stage 6：优化器与块裁剪

## 目标

完成规则优化与文件索引级裁剪。

## 任务

- constant folding；
- predicate normalization；
- projection pruning；
- predicate pushdown；
- aggregate/limit pushdown；
- min/max pruning；
- null_count pruning；
- dictionary negative check；
- 三值块判定；
- 优化规则 trace。

## 前端

- 展示优化前/后计划；
- 列块状态：
  - 未判定；
  - 元数据检查；
  - 跳过；
  - 待读取。
- 点击块显示跳过理由。

## 验收

- 选择性合成数据按预期跳过块。
- 未被投影的列文件不打开 payload。
- 字典无目标值时不扫描 codes。
- AND/OR 块判断正确。
- Explain 显示应用规则。
- 前端状态来自真实优化结果。

---

# Stage 7：物理执行与压缩态算子

## 目标

完成正式查询主链路。

## 任务

- BlockScan；
- cache；
- RawFilter；
- RLEFilter；
- DictionaryFilter；
- BitmapAnd/Or；
- Materialize；
- HashAggregate；
- Sort；
- Limit；
- 跨块 partial aggregate merge；
- 查询取消；
- 内存预算；
- per-operator metrics。

## 前端

- 执行中实时状态；
- 物理计划；
- operator metrics；
- 结果虚拟表格；
- 扫描/跳过/解码统计；
- 活动块描边与状态变化。

## 验收

- 查询结果与 DuckDB/Pandas 参照一致。
- 多列 AND/OR 使用 selection bitmap。
- RLE 聚合不展开全部值。
- Dictionary GROUP BY 不先恢复全部字符串。
- LIMIT 可提前停止。
- 取消后释放资源。
- 查询统计真实可复现。
- 生产 API 无 Pandas 查询路径。

---

# Stage 8：核心工作区完成

## 目标

将参考效果图完整实现为可用产品界面。

## 页面

### Workspace

- 数据结构；
- 列块轨道；
- 块检查器；
- 编码候选；
- 执行轨迹；
- 状态栏。

### Query

- SQL；
- 构造器；
- 结果；
- explain；
- profile；
- history。

### Compression Lab

- 数据分布；
- 候选算法；
- 编码结构；
- 对比指标。

## 交互

- 面板拖拽；
- 折叠；
- 尺寸持久化；
- 键盘选择；
- 工具提示；
- 错误状态；
- 空状态；
- 大数据 windowing。

## 验收

- 与参考图整体结构、密度、灰度和低饱和倾向一致。
- 没有传统 Dashboard 首页。
- 没有彩色卡片矩阵。
- 编码不只靠颜色识别。
- 1366×768 可用。
- 1000+ 块不产生明显卡顿。
- UI 全部读取真实 API。

---

# Stage 9：压缩实验与性能基准

## 目标

形成可重复、可解释的实验系统。

## 任务

- 合成数据生成器；
- 固定 seed；
- 编码 benchmark；
- 查询 benchmark；
- 冷/热缓存；
- 块大小矩阵；
- 行式参照；
- 原始样本保存；
- 环境快照；
- CSV/PNG 导出。

## 前端

- 参数配置；
- 任务进度；
- 对比表；
- 柱状图/折线图；
- 原始样本；
- 实验结论提示不自动夸大。

## 验收

- 同配置可复现相近结果。
- 每项至少支持预热 + 多次重复。
- 展示均值、中位数、P95、标准差。
- 结果包含 commit、机器、seed。
- 不只展示单次耗时。
- 图表可导出。

---

# Stage 10：可靠性、测试与答辩封板

## 目标

将系统提升至可稳定演示和毕业设计验收水平。

## 任务

- 全量测试补齐；
- 文件损坏注入；
- 磁盘不足模拟；
- 上传中断；
- 查询取消；
- 并发只读查询；
- 删除与活动查询冲突；
- 性能回归；
- 安全检查；
- README；
- 一键启动；
- 示例数据；
- 演示脚本。

## 必备演示脚本

1. 登录。
2. 导入低基数/游程混合数据。
3. 展示真实导入阶段。
4. 打开存储映射。
5. 选择 DICT 块查看候选比较。
6. 选择 RLE 块查看游程。
7. 执行多列过滤和 GROUP BY。
8. 展示块裁剪、压缩态算子和局部解码。
9. 运行一次压缩实验。
10. 展示 CRC 损坏检测或测试结果。
11. 展示自动化测试通过。

## 验收

- `pytest` 全部通过。
- 前端 build 和 E2E 通过。
- 一键启动脚本可用。
- 从干净数据库可初始化。
- 示例数据可在合理时间导入。
- 演示主链路无手工修改数据库。
- 无固定假指标。
- 所有 P0/P1 清单完成或有明确书面例外。

---

## 推荐提交顺序

```text
01 scaffold-auth
02 design-system-shell
03 vectors-raw-codec
04 rle-codec
05 dictionary-codec
06 codec-selector
07 row-groups
08 binary-format-writer
09 binary-format-reader
10 catalog-and-migrations
11 streaming-upload
12 import-jobs
13 sql-logical-plan
14 optimizer-pruning
15 physical-filters
16 aggregates-materialize
17 query-observability
18 storage-map-ui
19 query-workbench-ui
20 compression-lab
21 benchmark-center
22 hardening
```

每个提交必须包含对应测试，禁止最后统一补测试。
