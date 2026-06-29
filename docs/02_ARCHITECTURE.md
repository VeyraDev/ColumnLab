# ColumnLab 系统架构与数据格式设计

> 文档编号：CL-ARC-001  
> 目标：为 Codex 提供不可歧义的系统结构、数据格式、算法接口和执行路径。

---

## 1. 总体架构决策

ColumnLab 采用模块化单体：

```text
Browser
  │ HTTP / SSE
  ▼
FastAPI API Layer
  ├── Auth
  ├── Catalog API
  ├── Import API
  ├── Query API
  └── Benchmark API
  │
  ▼
Application Services
  ├── ImportCoordinator
  ├── QueryCoordinator
  ├── BenchmarkCoordinator
  └── DatasetLifecycleService
  │
  ├───────────────┬──────────────────┬────────────────
  ▼               ▼                  ▼
Catalog DB    Column Engine       Observability
SQLAlchemy    pure Python         metrics/events
  │               │
  ▼               ▼
SQLite/PG     Binary column files
```

### 1.1 依赖方向

严格遵循：

```text
API → Application → Domain/Engine → Infrastructure
```

核心算法层不得导入 FastAPI、SQLAlchemy ORM Model 或前端概念。

### 1.2 新仓库策略

从 RetailInsight 白名单移植：

- FastAPI 初始化模式；
- SQLAlchemy Session 和配置模式；
- 认证、密码哈希、JWT；
- 前端 Vite/Vue/TS 配置；
- Axios 拦截器；
- 用户 Store。

不得移植：

- 原 MainLayout；
- 原主题；
- 原业务路由；
- 清洗、质量、统计、ML、图表页面；
- Pandas 数据加载与预览路径。

---

## 2. 推荐仓库结构

```text
ColumnLab/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── auth/
│   │   ├── core/
│   │   ├── api/
│   │   │   ├── datasets.py
│   │   │   ├── imports.py
│   │   │   ├── storage.py
│   │   │   ├── queries.py
│   │   │   └── benchmarks.py
│   │   ├── application/
│   │   │   ├── import_service.py
│   │   │   ├── query_service.py
│   │   │   ├── benchmark_service.py
│   │   │   └── lifecycle_service.py
│   │   ├── catalog/
│   │   │   ├── models/
│   │   │   ├── repositories/
│   │   │   └── schemas/
│   │   ├── engine/
│   │   │   ├── types.py
│   │   │   ├── format/
│   │   │   ├── storage/
│   │   │   ├── codecs/
│   │   │   ├── import_pipeline/
│   │   │   ├── query/
│   │   │   ├── cache/
│   │   │   └── diagnostics/
│   │   ├── jobs/
│   │   └── observability/
│   ├── tests/
│   │   ├── unit/
│   │   ├── property/
│   │   ├── integration/
│   │   ├── golden/
│   │   └── benchmark/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── stores/
│   │   ├── router/
│   │   ├── layouts/
│   │   ├── views/
│   │   ├── components/
│   │   │   ├── storage-map/
│   │   │   ├── block-inspector/
│   │   │   ├── execution-plan/
│   │   │   ├── query-editor/
│   │   │   ├── import-progress/
│   │   │   └── benchmark/
│   │   ├── design-system/
│   │   └── workers/
│   └── tests/
├── docs/
├── samples/
└── scripts/
```

---

## 3. 元数据模型

元数据库只保存目录、任务、统计和权限；业务数据本体保存在列文件。

### 3.1 User

沿用认证用户模型。

### 3.2 Dataset

```text
id
user_id
name
description
source_file_name
source_sha256
status
active_version_id
created_at
updated_at
```

### 3.3 DatasetVersion

```text
id
dataset_id
version_no
storage_path
format_version
row_count
table_count
raw_bytes
encoded_bytes
status
created_at
```

### 3.4 Table

```text
id
dataset_version_id
name
row_count
row_group_count
created_at
```

### 3.5 Column

```text
id
table_id
ordinal
name
logical_type
nullable
scale
column_file_path
block_count
raw_bytes
encoded_bytes
min_value_json_for_catalog_only
max_value_json_for_catalog_only
```

说明：catalog 中的 min/max 可以使用数据库可查询格式，但列文件内部元数据必须为二进制；不得因为 catalog 中存在 JSON 就用 JSON 代替文件格式。

### 3.6 ColumnBlockCatalog

为前端快速浏览保存摘要，不作为查询真相来源：

```text
id
column_id
block_id
row_start
row_count
encoding
raw_bytes
encoded_bytes
null_count
distinct_count
min_repr
max_repr
run_count
dictionary_count
payload_crc32
```

### 3.7 ImportJob

包含状态机、进度、错误分类、临时路径和结果版本。

### 3.8 QueryExecution

保存 SQL、逻辑计划 JSON、物理计划 JSON、状态、统计和错误。计划 JSON 仅是 API 表示，不是列式存储格式。

### 3.9 BenchmarkRun / BenchmarkSample

保存实验配置、环境信息、每次样本和汇总。

---

## 4. 逻辑类型系统

定义稳定枚举：

```text
INT64        = 1
FLOAT64      = 2
BOOLEAN      = 3
UTF8         = 4
DATE32       = 5
TIMESTAMP64  = 6
DECIMAL64    = 7
```

### 4.1 规范化表示

- INT64：signed 64-bit little-endian。
- FLOAT64：IEEE 754 little-endian。
- BOOLEAN：bit-packed。
- UTF8：32/64-bit offsets + UTF-8 blob。
- DATE32：自 Unix epoch 起天数。
- TIMESTAMP64：UTC 微秒。
- DECIMAL64：scaled int64，scale 写入列 schema。
- NULL：独立 bitmap，不改变值域。

所有编码先接收规范化数组，而不是直接处理 Pandas dtype。

---

## 5. 行组与块设计

### 5.1 为什么使用共享行组

多列联合查询要求不同列对同一行范围具有稳定映射。若每列完全独立按 64 KiB 切分，会导致块边界不一致，显著增加 selection 对齐复杂度。

因此采用：

> 共享逻辑行组 + 每列一个对应物理列块。

所有列在同一个 row_group_id 下具有相同：

```text
row_start
row_count
```

### 5.2 行组切分算法

流式读取行，维护每列当前行组的 raw size estimator。

关闭行组条件：

```text
max(estimated_raw_bytes_per_column) >= target_block_bytes
OR row_count >= max_rows
OR end_of_input
```

同时保证：

```text
row_count >= min_rows
```

除非输入结束或遇到单行超大值。

默认：

```text
target_block_bytes = 65536
min_rows = 512
max_rows = 65536
```

字符串估算包括 offset 和 UTF-8 bytes；NULL bitmap 计入预算。

### 5.3 物理块大小

64 KiB 是目标而非固定整齐填满。由于压缩后大小不确定，块 payload 可以小于目标。块头必须保存 raw 和 encoded 大小。

---

## 6. 二进制列文件格式

文件使用 little-endian，所有结构明确版本化并按 8 字节对齐。

### 6.1 文件布局

```text
+--------------------+
| File Header        |
+--------------------+
| Block 0 Header     |
| Block 0 Stats      |
| Block 0 Payload    |
+--------------------+
| ...                |
+--------------------+
| Block Index        |
+--------------------+
| File Footer        |
+--------------------+
```

### 6.2 File Header

固定 64 字节，建议字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| magic | char[8] | `CLCOL001` |
| format_version | uint16 | 文件格式版本 |
| header_size | uint16 | 当前头长度 |
| logical_type | uint8 | 类型枚举 |
| flags | uint8 | nullable 等 |
| reserved | uint16 | 保留 |
| column_id | uint64 | catalog column id |
| total_rows | uint64 | 总行数 |
| block_count | uint32 | 块数 |
| target_block_bytes | uint32 | 目标块大小 |
| footer_offset | uint64 | Footer 起点 |
| schema_fingerprint | uint64 | schema hash |
| created_at_epoch | uint64 | 创建时间 |
| header_crc32 | uint32 | 头校验 |
| padding | bytes | 对齐至64 |

写入初期 footer_offset 与 block_count 可为0，最终提交前回填并重算 CRC。

### 6.3 Block Header

固定头建议 64 或 80 字节，必须包含：

| 字段 | 类型 |
|---|---|
| magic `BLK1` | char[4] |
| header_size | uint16 |
| encoding | uint8 |
| flags | uint8 |
| block_id | uint32 |
| row_group_id | uint32 |
| row_start | uint64 |
| row_count | uint32 |
| null_count | uint32 |
| distinct_count | uint32 |
| raw_bytes | uint32/uint64 |
| encoded_bytes | uint32/uint64 |
| stats_bytes | uint32 |
| payload_crc32 | uint32 |
| run_count_or_dict_count | uint32 |
| reserved | bytes |

固定头后跟 typed stats：

```text
min_length + min_bytes
max_length + max_bytes
optional codec diagnostics
```

### 6.4 Payload 通用前缀

```text
null_bitmap_length: uint32
null_bitmap
codec_payload
```

### 6.5 RAW Payload

固定宽度：

```text
contiguous values
```

UTF8：

```text
offset_width: uint8
offset_count: uint32
offsets
utf8_blob
```

### 6.6 RLE Payload

```text
run_count
[value][varint run_length] × run_count
```

NULL 不作为特殊值进入 run，NULL 位置由 bitmap 表示。实现时必须定义 NULL 是否打断游程，并通过测试固定行为。推荐 NULL 打断游程。

### 6.7 Dictionary Payload

```text
dictionary_count
dictionary_encoding_metadata
dictionary_values
code_bit_width
packed_codes_length
packed_codes
```

字典值使用与 RAW 相同的逻辑类型编码。codes 必须位打包，不得以 Python int 数组或文本落盘。

### 6.8 Block Index

Index 使查询只读取文件尾即可获得：

```text
block_id
row_group_id
offset
total_block_length
row_start
row_count
encoding
null_count
min_value
max_value
payload_crc32
```

Index 自身有 CRC。

### 6.9 Footer

```text
magic = CLFTR001
index_offset
index_length
column_raw_bytes
column_encoded_bytes
column_min
column_max
file_crc32 or metadata_crc32
footer_size
```

### 6.10 Reader 行为

1. 读取 Header。
2. 验证 magic/version/header CRC。
3. 定位 Footer。
4. 验证 Footer/Index。
5. 将 Block Index 载入内存。
6. 按需 seek 读取块。
7. 验证 payload CRC。
8. 解码或调用压缩态算子。

---

## 7. Codec 接口

定义纯 Python 协议：

```python
class Codec(Protocol):
    encoding_id: Encoding

    def encode(self, values: ValueVector, nulls: NullBitmap) -> EncodedBlock: ...
    def decode(self, block: EncodedBlock) -> ValueVector: ...
    def estimate_capabilities(self) -> CodecCapabilities: ...
    def filter(self, block, predicate) -> SelectionVector | NotSupported: ...
    def aggregate(self, block, aggregate) -> PartialAggregate | NotSupported: ...
```

### 7.1 EncodedBlock

```text
encoding
payload
raw_bytes
encoded_bytes
null_count
distinct_count
min_value
max_value
run_count
dictionary_count
encode_ns
diagnostics
```

### 7.2 编码选择器

对每个行组列块：

```text
raw = RawCodec.encode(...)
rle = RleCodec.encode(...)
dict = DictionaryCodec.encode(...)

candidate_results = [raw, rle, dict]
```

选择逻辑：

1. 过滤不支持该逻辑类型的候选。
2. 按实际 `encoded_bytes` 排序。
3. 若最优相对 RAW 收益 `< min_gain`，选 RAW。
4. 若前两名差异 `< tie_threshold`，使用固定 decode cost 等级和算子能力决胜。
5. 保存全部候选诊断。
6. 选择过程必须确定性。

推荐默认：

```text
min_gain = 0.05
tie_threshold = 0.02
```

---

## 8. 导入管线

### 8.1 阶段

```text
Upload
→ Validate
→ Parse stream
→ Infer schema
→ Normalize values
→ Build shared row groups
→ Encode candidates
→ Write column blocks
→ Write indexes/footer
→ Validate round trip
→ Commit version
```

### 8.2 流式策略

CSV 使用增量 parser。XLSX 使用 openpyxl `read_only=True`。

禁止先将完整数据加载为 DataFrame。

### 8.3 写入器

每列保持独立 `ColumnWriter`。一个行组形成后：

1. 每列生成规范化 `ValueVector`；
2. 生成候选编码；
3. 选择编码；
4. 写 Block Header/Stats/Payload；
5. 保存 index entry；
6. 释放行组内存。

### 8.4 最终验证

提交前至少执行：

- 每列行数一致；
- 所有 row_group 范围一致；
- Header/Index/Footer CRC；
- 随机块 round-trip；
- 首块、末块 round-trip；
- 数据集 schema fingerprint；
- encoded bytes 与文件大小一致性。

可配置 `full_verify` 对全部块解码校验。

---

## 9. 查询引擎

### 9.1 SQL Parser

使用 sqlglot 仅负责解析。解析后转换为内部不可变表达式：

```text
ColumnRef
Literal
Compare
And / Or / Not
In
Between
IsNull
AggregateExpr
```

禁止把 SQL 直接交给 SQLite、DuckDB 或 Pandas 执行。

### 9.2 逻辑计划

```text
Scan(table)
Filter(predicate)
Project(expressions)
Aggregate(group_keys, aggregates)
Sort(keys)
Limit(limit, offset)
```

### 9.3 优化器规则顺序

推荐固定点迭代：

1. Validate references/types
2. Constant folding
3. Predicate normalization
4. Projection pruning
5. Predicate pushdown
6. Aggregate pushdown
7. Limit pushdown
8. Block pruning annotations
9. Physical capability selection

规则执行必须在 explain 中可见。

### 9.4 块裁剪

根据 predicate 与 index stats 判断：

- `col > x` 且 `max <= x`：跳过；
- `col = x` 且 `x < min or x > max`：跳过；
- `IS NULL` 且 `null_count = 0`：跳过；
- 字典不包含目标值：加载字典元数据后快速否定；
- 组合条件使用三值判定：`ALWAYS_FALSE / MAYBE / ALWAYS_TRUE`。

### 9.5 选择向量

每个 row_group 使用：

```text
SelectionVector
- all
- none
- bitmap
- sorted row offsets
```

AND/OR 在 bitmap 层合并。不得物化完整行对象后再合并。

### 9.6 物理算子

#### BlockScan

读取指定列和 row_group。读取前咨询 cache。

#### RawFilter

对紧凑向量执行 NumPy/自定义批量比较。

#### RLEFilter

直接输出符合游程对应的 offset 范围或 bitmap，不展开所有值。

#### DictionaryFilter

将 literal 映射到 code，再比较 packed codes；IN 转 code set。

#### Materialize

只对最终需要输出的列和选中行解码。

#### HashAggregate

按 group code 或实际值维护部分聚合。跨块归并。

#### Sort

仅在 ORDER BY 时使用；允许对最终结果排序，不应对整表提前物化。

### 9.7 压缩态聚合

RLE：

```text
COUNT = Σ run_length (排除 NULL)
SUM = Σ value × run_length
MIN/MAX = run values
AVG = SUM / COUNT
```

Dictionary GROUP BY：

```text
group count by code
merge dictionary value at output boundary
```

带 selection 时，算子只计算选择范围。不能为方便而默认完整解码。

### 9.8 并发模型

- API 使用 async 负责 I/O 协调；
- CPU 密集编码/查询放入受控线程池或进程池；
- 单任务内部并发度可配置，默认 `min(4, cpu_count)`；
- 同一数据集版本只读查询可并发；
- 导入提交期间版本不可见；
- 删除操作需等待活动引用释放或标记延迟删除。

---

## 10. 缓存

### 10.1 Cache Key

```text
(version_id, column_id, block_id, representation)
```

representation 可为：

- encoded bytes；
- dictionary metadata；
- decoded vector。

### 10.2 约束

- 字节容量上限；
- LRU；
- 线程安全；
- 统计命中率；
- 数据集删除或版本切换时失效；
- benchmark 可关闭缓存。

---

## 11. API 设计

统一响应可沿用：

```json
{"code": 0, "data": {}, "msg": "ok"}
```

### 11.1 数据集

```text
POST   /api/datasets/uploads
GET    /api/datasets
GET    /api/datasets/{id}
DELETE /api/datasets/{id}
GET    /api/datasets/{id}/tables
GET    /api/tables/{id}/columns
```

### 11.2 导入任务

```text
GET    /api/import-jobs/{job_id}
GET    /api/import-jobs/{job_id}/events
POST   /api/import-jobs/{job_id}/cancel
```

`events` 使用 SSE。

### 11.3 存储观察

```text
GET /api/tables/{table_id}/storage-map
GET /api/columns/{column_id}/blocks
GET /api/columns/{column_id}/blocks/{block_id}
GET /api/columns/{column_id}/blocks/{block_id}/preview
```

### 11.4 查询

```text
POST /api/queries
GET  /api/queries/{query_id}
GET  /api/queries/{query_id}/events
POST /api/queries/{query_id}/cancel
GET  /api/queries/{query_id}/result
GET  /api/queries/{query_id}/explain
```

### 11.5 基准实验

```text
POST /api/benchmarks
GET  /api/benchmarks/{id}
GET  /api/benchmarks/{id}/events
GET  /api/benchmarks/{id}/samples
```

---

## 12. 前端架构

### 12.1 路由

```text
/login
/workspace/:datasetId
/imports
/query/:datasetId
/compression-lab/:datasetId?
/benchmarks
/settings
```

登录后默认进入最近数据集的 workspace；无数据集进入导入空状态。

### 12.2 Store

建议拆分：

```text
authStore
datasetStore
storageMapStore
importJobStore
queryStore
benchmarkStore
workspaceLayoutStore
```

不得把所有状态放入一个 dataset store。

### 12.3 核心组件

```text
StorageMapCanvas
ColumnTrack
BlockCell
EncodingLegend
BlockInspector
CodecCandidateTable
ExecutionPlanTree
OperatorMetrics
QueryEditor
ResultGrid
ImportPipeline
BenchmarkConfigurator
```

### 12.4 列块渲染

块数量大时只渲染可视区域。可以：

- CSS Grid + windowing；
- Canvas；
- WebGL（非必要）。

优先采用可访问性更好的 DOM windowing。需要工具提示和键盘选择。

### 12.5 设计 Token

```css
--bg-app: #F3F3F0;
--bg-panel: #FAFAF7;
--bg-raised: #FFFFFF;
--bg-muted: #EEEFEA;

--text-primary: #242621;
--text-secondary: #666B62;
--text-tertiary: #92978E;

--border-default: #D8DAD3;
--border-strong: #BFC3B8;

--accent: #747F62;
--accent-hover: #657055;
--accent-soft: #E4E7DE;

--success: #647C61;
--warning: #8A775B;
--danger: #8A625E;

--radius-panel: 4px;
--radius-control: 4px;
```

核心面板无常驻阴影。Element Plus 默认样式必须覆盖。

---

## 13. 故障处理

### 13.1 导入故障

- 解析错误；
- 类型错误；
- 磁盘空间不足；
- 编码异常；
- CRC 验证失败；
- 用户取消。

全部进入结构化 error_code，清理 staging，不发布版本。

### 13.2 查询故障

- SQL 语法；
- 不支持语法；
- 列不存在；
- 类型不兼容；
- 数据文件缺失；
- CRC 损坏；
- 内存预算超限；
- 用户取消。

不得返回部分结果冒充完整结果。

### 13.3 数据损坏

数据集状态标记 `degraded`，前端显示损坏列块。允许用户执行完整校验，不允许静默跳过损坏块。

---

## 14. 测试架构

### 14.1 Codec 属性测试

使用 Hypothesis：

- 随机长度；
- NULL；
- 极值；
- Unicode；
- 长游程；
- 单一值；
- 全唯一；
- 空块；
- 最大 run length；
- bit width 边界 1/2/4/8/16。

### 14.2 文件格式测试

- golden 文件；
- 版本拒绝；
- header CRC；
- payload CRC；
- 截断文件；
- 错误 footer offset；
- index 损坏；
- 跨版本读取测试。

### 14.3 查询正确性

对随机表和 SQL 子集：

```text
ColumnLab result == DuckDB/Pandas reference
```

比较时处理顺序、NULL 和浮点容差。

### 14.4 集成测试

覆盖完整链路：

```text
upload → import → query → explain → delete
```

### 14.5 性能测试

性能测试单独运行，记录：

- 机器环境；
- Python 版本；
- commit；
- 数据种子；
- 配置；
- 原始样本。

---

## 15. 架构验收原则

只有当数据从自定义列文件读取、通过自己的计划与算子执行、前端展示真实引擎状态时，才能认为系统主链路完成。

任何为了快速演示而绕过引擎的“备用 Pandas 路径”，不得出现在生产 API 中。
