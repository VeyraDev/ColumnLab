# ColumnLab 答辩演示脚本

## 前置

1. 运行 `scripts/start.ps1`（Windows）或 `scripts/start.sh`（Linux/macOS）
2. 浏览器打开 http://127.0.0.1:5173
3. 注册/登录演示账号

## UI 逐步演示

### 1. 登录
- 访问 `/login`，输入用户名与密码
- **预期**：进入工作区

### 2. 导入 demo_rle.csv
- 功能轨道 → **数据导入**
- 上传 `samples/demo_rle.csv`，表名 `data`，strict 模式
- **预期**：导入完成，状态 ready；qty/status 列可见 RLE 友好块

### 3. 工作区存储映射
- 返回工作区，查看列块映射与块检查器
- **预期**：块纹理区分 RAW/RLE/DICT；点击块显示编码详情

### 4. 查询执行
- 功能轨道 → **查询执行**
- SQL：`SELECT status, COUNT(*) AS c FROM data GROUP BY status`
- **预期**：执行轨迹、块裁剪、结果表

### 5. 压缩实验（块级预览）
- 功能轨道 → **压缩实验**
- 选择列与块，查看 codec 候选表
- **预期**：RLE/DICT 候选与 winner 说明

### 6. 性能基准中心
- 压缩实验页点击 **打开性能基准中心**，或访问 `/benchmarks`
- 配置 seed=42、run_length、重复 3 次，提交实验
- **预期**：进度 SSE、对比表含 mean/p95、SVG 图表、结论摘要
- 导出 CSV/JSON

### 7. 可选：demo_dict / demo_mixed
- 分别导入 `samples/demo_dict.csv`、`samples/demo_mixed.csv`
- 对比 DICT 与 GROUP BY 场景

## API 自动化演示

```bash
cd backend
pip install httpx
python ../scripts/demo_flow.py
```

## 截图建议点

1. 工作区三栏 + 执行轨迹四栏布局
2. 存储映射 RLE 长条块
3. 查询块裁剪统计
4. Benchmark 对比表与 SVG 柱状图
