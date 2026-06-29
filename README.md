# ColumnLab

列式存储实验平台 — 后端 FastAPI + 前端 Vue 3。

## 目录结构

```
ColumnLab/
├── backend/          # FastAPI 后端 + 列式引擎 (app/engine/)
├── frontend/         # Vue 3 + Vite 前端
├── docs/             # 需求、架构与分阶段计划
├── samples/          # 示例数据
└── scripts/          # 一键启动与 API 演示脚本
```

## 一键启动

**Windows (PowerShell):**

```powershell
./scripts/start.ps1
```

**Linux / macOS:**

```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

手动启动见下方「快速启动」。

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 http://127.0.0.1:5173

## 示例数据集

| 文件 | 用途 |
|------|------|
| `samples/basic.csv` | 基础导入测试 |
| `samples/demo_rle.csv` | 长游程，展示 RLE 压缩 |
| `samples/demo_dict.csv` | 低基数列，展示 DICT |
| `samples/demo_mixed.csv` | 多列 + GROUP BY 演示 |

## 演示流程

- 人工答辩步骤：[docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- API 自动化（需后端已启动）：

```bash
pip install httpx
python scripts/demo_flow.py
```

## 测试命令

| 命令 | 说明 |
|------|------|
| `cd backend && pytest` | 单元 + 集成 + 可靠性测试 |
| `cd frontend && npm run build` | 前端生产构建 |
| `cd frontend && npx playwright install chromium` | 首次 E2E 需安装浏览器 |
| `cd frontend && npm run build && npm run test:e2e` | Playwright 冒烟 E2E |

### Benchmark

- UI：访问 `/benchmarks` 或通过压缩实验页进入性能基准中心
- API：`POST /api/benchmarks` → `GET /api/benchmarks/{id}` / `samples` / `export.csv`

## 主要功能

- 列式导入、存储映射、块检查器、SQL 查询与块裁剪
- 压缩实验（块级 codec 预览）
- 性能基准中心（seed 可复现、mean/median/p95/stdev、CSV/JSON 导出）
