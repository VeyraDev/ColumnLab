# ColumnLab 最终验收清单

> 使用方法：逐项打勾。P0 未完成不得交付；P1 未完成必须有明确原因和替代方案。

---

## A. 工程与复用策略

- [ ] P0 使用独立 ColumnLab 仓库。
- [ ] P0 仅白名单移植 RetailInsight 基础设施。
- [ ] P0 无 RetailInsight 业务路由、旧主题和旧主布局残留。
- [ ] P0 核心引擎不依赖 FastAPI/SQLAlchemy。
- [ ] P0 前后端可独立构建和测试。

## B. 导入

- [ ] P0 上传为流式写入，不一次性读取完整文件。
- [ ] P0 CSV 可用。
- [ ] P0 XLSX read-only 可用。
- [ ] P0 类型推断可覆盖。
- [ ] P0 strict/coerce 可用。
- [ ] P0 ImportJob 状态完整。
- [ ] P0 进度来自真实处理。
- [ ] P0 staging + atomic commit。
- [ ] P0 失败不暴露半成品。
- [ ] P1 可取消并清理。

## C. 行组与文件格式

- [ ] P0 多列共享 row_group 范围。
- [ ] P0 目标字节大小参与切分。
- [ ] P0 每列独立 `.col`。
- [ ] P0 文件含 Header/Block/Index/Footer。
- [ ] P0 存储不是 JSON/CSV/Pickle。
- [ ] P0 有 magic/version。
- [ ] P0 有 NULL bitmap。
- [ ] P0 有 min/max。
- [ ] P0 有 payload CRC32。
- [ ] P0 Index 可支持不读取 payload 的裁剪。
- [ ] P0 原子 finalize。
- [ ] P0 golden test。
- [ ] P0 损坏/截断测试。

## D. 编码

- [ ] P0 RAW 完整。
- [ ] P0 RLE 编解码。
- [ ] P0 RLE filter。
- [ ] P0 RLE aggregate。
- [ ] P0 Dictionary 编解码。
- [ ] P0 codes bit packing。
- [ ] P0 Dictionary equality/IN。
- [ ] P0 Dictionary GROUP BY。
- [ ] P0 每块实际生成候选编码。
- [ ] P0 5% 最低收益阈值。
- [ ] P0 候选大小与选择原因可展示。
- [ ] P0 属性测试覆盖边界。

## E. SQL 与查询

- [ ] P0 SELECT/WHERE。
- [ ] P0 AND/OR/NOT。
- [ ] P0 IN/BETWEEN/IS NULL。
- [ ] P0 COUNT/SUM/AVG/MIN/MAX。
- [ ] P0 GROUP BY。
- [ ] P0 ORDER BY。
- [ ] P0 LIMIT/OFFSET。
- [ ] P0 不支持语法明确报错。
- [ ] P0 内部逻辑计划。
- [ ] P0 内部物理计划。
- [ ] P0 投影裁剪。
- [ ] P0 谓词下推。
- [ ] P0 块裁剪。
- [ ] P0 字典快速否定。
- [ ] P0 LIMIT 提前终止。
- [ ] P0 bitmap 多列合并。
- [ ] P0 压缩态算子。
- [ ] P0 只在必要时局部解码。
- [ ] P0 与参照引擎结果一致。
- [ ] P1 查询取消。

## F. 可观测性

- [ ] P0 parse/optimize/execute 耗时。
- [ ] P0 总块/跳过/扫描。
- [ ] P0 bytes_read。
- [ ] P0 rows_examined/output。
- [ ] P0 compressed/decoded blocks。
- [ ] P0 每算子输入输出与耗时。
- [ ] P0 cache 命中。
- [ ] P0 request_id/job_id/query_id。
- [ ] P0 错误分类。

## G. 前端

- [ ] P0 视觉结构符合参考图。
- [ ] P0 无 Dashboard 统计卡阵列。
- [ ] P0 无渐变。
- [ ] P0 无彩色图标底板。
- [ ] P0 无大圆角和常驻阴影。
- [ ] P0 中性色占主导。
- [ ] P0 RAW/RLE/DICT 用纹理区分。
- [ ] P0 存储映射来自真实后端。
- [ ] P0 块检查器完整。
- [ ] P0 编码候选表完整。
- [ ] P0 查询执行状态联动。
- [ ] P0 执行计划与指标。
- [ ] P0 导入真实进度。
- [ ] P0 查询结果虚拟滚动。
- [ ] P0 1366×768 可用。
- [ ] P0 1600×900 可用。
- [ ] P1 面板可调整并持久化。
- [ ] P1 1000+ 块窗口化渲染。

## H. 实验

- [ ] P0 合成数据支持固定 seed。
- [ ] P0 连续游程数据。
- [ ] P0 低基数数据。
- [ ] P0 高基数数据。
- [ ] P0 NULL 与混合数据。
- [ ] P0 RAW/RLE/DICT 对比。
- [ ] P0 块大小对比。
- [ ] P0 裁剪开关对比。
- [ ] P0 完整解码/压缩态对比。
- [ ] P0 冷/热缓存。
- [ ] P0 预热与重复次数。
- [ ] P0 均值/中位数/P95/标准差。
- [ ] P0 原始样本保存。
- [ ] P0 环境与 commit 保存。

## I. 禁止项复核

- [ ] 没有 Pandas 正式查询路径。
- [ ] 没有整表默认加载。
- [ ] 没有查询前完整解压。
- [ ] 没有 JSON 列文件。
- [ ] 没有只按数据类型写死算法。
- [ ] 没有以 Parquet/DuckDB 代替核心。
- [ ] 没有假进度。
- [ ] 没有假压缩率或假耗时。
- [ ] 没有仅前端模拟执行计划。
- [ ] 没有“能运行即完成”的未测代码。

## J. 最终演示

- [ ] 从空系统注册登录。
- [ ] 上传文件并观察导入阶段。
- [ ] 查看存储映射。
- [ ] 查看 RLE 块。
- [ ] 查看 DICT 块。
- [ ] 查看候选编码。
- [ ] 执行多列查询。
- [ ] 展示块裁剪。
- [ ] 展示压缩态聚合。
- [ ] 展示查询指标。
- [ ] 运行性能实验。
- [ ] 展示测试结果。
- [ ] 展示损坏文件检测。
