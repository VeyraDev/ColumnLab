# ColumnLab 开发指令包

> 版本：v1.0  
> 日期：2026-06-29  
> 用途：作为 Codex 实施 ColumnLab 列式存储与列压缩数据库系统的最高优先级需求与验收依据。

## 1. 阅读顺序

1. `01_REQUIREMENTS.md`：明确系统必须实现什么、不得如何简化。
2. `02_ARCHITECTURE.md`：明确系统如何分层、数据怎样落盘、算法和查询怎样执行。
3. `03_IMPLEMENTATION_PLAN.md`：明确开发顺序、阶段交付物和每阶段验收条件。
4. `04_ACCEPTANCE_CHECKLIST.md`：最终逐项验收，任何 P0/P1 项未通过均不得宣称完成。
5. `assets/columnlab-workbench-reference.png`：前端核心工作区视觉参考。

## 2. 项目定位

ColumnLab 是一个单机、多用户、可观测的列式存储与压缩查询引擎原型。系统必须真实完成：

- 流式导入结构化数据；
- 按列、按共享行组组织数据；
- 以约 64 KiB 为目标大小生成二进制列块；
- 实现 RAW、RLE、Dictionary + bit packing；
- 每块实际比较候选编码后自适应选择；
- 支持 SQL 子集、多列联合过滤、聚合与分组；
- 实现列裁剪、谓词下推、块裁剪、字典快速否定、压缩态过滤和压缩态聚合；
- 展示块元数据、编码竞争结果、查询执行计划和真实运行指标；
- 通过自动化测试、正确性对照、损坏文件检测和可重复性能实验验证。

系统不是“压缩算法演示程序”，也不是 RetailInsight 的换皮版本。

## 3. 已定技术路线

- 新建独立仓库，暂名 `ColumnLab`。
- 选择性移植 RetailInsight 的认证、FastAPI/SQLAlchemy 基础、Axios 拦截器、Vue/Vite/TypeScript 配置。
- 不移植 RetailInsight 的主布局、主题、首页、数据质量、清洗、统计、机器学习、图表业务页面。
- 前端：Vue 3 + TypeScript + Vite + Pinia；Element Plus 仅作为基础控件库，核心工作区自定义实现。
- 后端：Python 3.11+、FastAPI、SQLAlchemy、Pydantic。
- 元数据库：开发默认 SQLite，保持 PostgreSQL 可切换能力。
- 数据存储：自定义二进制列文件；严禁用 JSON、CSV、Pickle 或 DataFrame 文件冒充列式格式。
- SQL 解析：允许使用 `sqlglot` 生成 AST，但查询优化和执行必须自行实现。
- 进度通道：导入和查询任务通过 SSE 推送，轮询作为降级方案。
- 测试：pytest + Hypothesis；查询结果以 DuckDB 或 Pandas 作为仅用于测试的正确性参照。

## 4. 运行期限制（当前实现）

以下状态保存在**单进程内存**中，应用重启或多 worker 部署后会丢失：

| 模块 | 内存结构 | 影响 |
|------|----------|------|
| 导入协调器 | `_cancel_flags`、`_event_buffers` | 取消信号与 SSE 事件缓冲 |
| 查询执行器 | `_cancel_flags`、`_event_buffers`、`_active_queries` | 查询取消与进度事件 |
| Benchmark | `_event_buffers` | 运行进度 SSE |

**课程演示**默认单进程 + daemon 线程即可；若需毕业设计级可靠性，取消标志与关键事件应持久化到数据库或 Redis，SSE 通过共享事件总线广播。

列文件索引中的 min/max 统计使用 **stats_offset / stats_length** 指向块内完整 typed stats blob，Footer 使用 **column_stats_offset / column_stats_length**，避免 8 字节截断导致 UTF-8 或整数尾部零字节解码错误。

## 5. 关键原则

1. 架构保持单体分层，不做无意义微服务化。
2. 核心实现不得简化：真实二进制文件、真实分块、真实压缩、真实查询执行。
3. 所有前端指标必须来自后端真实执行，不得使用固定演示数字。
4. 不以“能运行”为完成标准，以可解释、可验证、可重复为完成标准。
5. 遇到文档与临时代码冲突，以本指令包为准。
