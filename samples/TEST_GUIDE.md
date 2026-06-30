# ColumnLab 后端算法测试集使用说明

## 1. 使用规则

- 所有 CSV 默认表名使用 `data`。
- 算法正确性测试优先使用 **4 KiB 或 16 KiB**，便于产生多个块、观察块裁剪。
- 性能实验使用 **64 KiB** 默认块，避免把演示参数当成正式实验参数。
- 每个文件单独导入为一个数据集。
- 查询结果必须与 `expected_results.json` 完全一致；浮点 AVG 允许极小误差。
- 编码类型是预期趋势，不要求每个块百分之百同一编码；最终以块检查器中的实际候选字节数为准。

## 2. 测试顺序

1. `01_rle_runs.csv`
   - 检查 phase/qty 是否大多选择 RLE。
   - 运行 RLE 过滤与聚合 SQL。
   - 关注 `compressed_operator_blocks > 0`、`decoded_blocks` 尽量低。

2. `02_dictionary_low_cardinality.csv`
   - 检查 region/category/channel 是否大多选择 DICTIONARY。
   - 验证等值、IN 和 GROUP BY。
   - 检查 bit width 与字典条目数。

3. `03_raw_high_cardinality.csv`
   - token/hash_like 不应为了“有字典算法”而强制选择 DICTIONARY。
   - 候选收益低于阈值时应回退 RAW。

4. `04_pruning_multicolumn.csv`
   - 重点运行 AND/OR 两条查询。
   - AND 查询必须返回 0。
   - 查询 Profile 中应看到明显块裁剪。
   - `region='missing-region'` 应通过字典快速否定跳过相关块。

5. `05_mixed_aggregate_dictionary.csv`
   - 重点检查混合聚合结果。
   - 若 COUNT 被重复累计，说明压缩态聚合部分执行后回退存在副作用。

6. `06_types_nulls_unicode.csv`
   - 使用列类型覆盖：
     - id/int_value → INT64
     - float_value → FLOAT64
     - bool_value → BOOLEAN
     - text_value → UTF8
     - date_value → DATE32
     - timestamp_value → TIMESTAMP64
     - decimal_value → DECIMAL64，scale=2

7. `06b_invalid_strict_coerce.csv`
   - strict：应在首次无效值处失败。
   - coerce：应成功导入，错误单元格置 NULL，错误计数应为 6。

8. `07_realistic_orders_100k.csv`
   - 用于综合性能、冷/热缓存、裁剪开关和不同块大小对比。
   - 这是合成业务数据，不应在报告中称为真实公开数据集。

9. `08_xlsx_import_sample.xlsx`
   - 验证 XLSX 只读导入和日期单元格处理。

## 3. 必测后端断言

- `decode(encode(values)) == values`
- 同一行组中所有列的 `row_start`、`row_count` 一致
- 被裁剪块不增加 `bytes_read`
- 相同物理块的 `scanned_blocks` 只计一次
- 缓存命中增加 `cache_hits`，但不增加真实磁盘 `bytes_read`
- 同一块最多完整解码一次
- LIMIT 不得穿过 Filter/Aggregate/Sort
- AND 中任一谓词块判定为 ALWAYS_FALSE 时，该块最终 selection 必须为空
- 压缩态聚合失败回退前不得修改正式聚合状态
- 损坏 payload 必须触发 CRC 错误

## 4. CRC 测试

先导入任一数据集，找到生成的 `.col` 文件，然后运行：

```bash
python corrupt_column_file.py <path/to/column.col>
```

用生成的 `.corrupted.col` 替换测试副本后读取，系统应报 CRC mismatch，不得返回结果。

## 5. 数据规模建议

- 快速回归：01～06，通常数秒到几十秒。
- 综合演示：07，100,000 行。
- 正式性能实验：可将 07 扩大至 500,000 或 1,000,000 行，并保持固定随机种子。
