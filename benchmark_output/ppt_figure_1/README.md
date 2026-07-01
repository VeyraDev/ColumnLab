# ColumnLab PPT 图1实验结果

本目录由 `scripts/run_ppt_codec_benchmark.py` 自动生成。

## 参数（本次运行）
- 行数：100000
- 预热：2
- 重复：5
- 随机种子：42
- 块大小配置：65536 B
- 编码：RAW、RLE、DICTIONARY
- 分布：长游程、低基数、高基数

## 文件
- `ppt_fig1_codec_relative_size.csv`：PPT图直接使用的数据。
- `ppt_fig1_codec_relative_size.svg`：黑白灰矢量图，可直接插入PPT。
- `codec_benchmark_all_columns.csv`：qty和region全部指标。
- `codec_benchmark_raw.json`：每组benchmark完整summary。

纵轴采用 `encoded_bytes / RAW encoded_bytes × 100%`，RAW固定为100%。

注意：当前ColumnLab codec benchmark的 `block_sizes` 字段作为实验配置记录；
编码指标来自当前benchmark引擎对生成列向量的实际RAW/RLE/DICTIONARY编码结果。
