# 测试指南

本文档说明如何运行 Log Assistant 的自动化测试、测试覆盖范围，以及如何编写新测试。

## 快速运行

```bash
# 后端测试（15 个用例）
pytest -v

# 前端测试（23 个用例）
cd frontend
npm test

# 前端构建验证
cd frontend
npm run build

# 性能基准测试（10 万行日志）
docker compose exec api python tools/perf_benchmark.py
```

## 后端测试

### 测试框架

- **pytest** + **httpx**（FastAPI TestClient）
- 测试文件位于 `tests/`

### 测试文件说明

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `test_auth_service.py` | 6 | 注册（密码哈希、重复邮箱）、登录（Token 签发、错误密码）、Cookie 鉴权、Refresh Token |
| `test_health.py` | 2 | 健康检查路由注册、响应格式 |
| `test_log_parser.py` | 5 | 日志解析（时间戳/级别/服务名提取）、Token 解码、跨用户数据隔离（404）、分析任务内部 ID 映射 |
| `test_task_queue.py` | 1 | Redis 任务提交与队列写入 |
| `test_log_parser.py` | 1 | 用户隔离：其他用户无法触发不属于自己的日志分析 |

### 示例：编写后端测试

```python
# tests/test_example.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_rejects_empty_file():
    response = client.post(
        "/logs/upload",
        files={"file": ("empty.log", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
```

### 注意事项

- 后端测试使用 mock 数据库和 Redis，不需要真实的 PostgreSQL/Redis 连接
- `openai` 包在测试中被延迟导入，避免未安装时测试失败
- 测试间通过 mock 隔离，无相互依赖

## 前端测试

### 测试框架

- **Vitest** + **happy-dom**
- 测试文件位于 `frontend/src/__tests__/`

### 测试文件说明

| 文件 | 测试数 | 覆盖内容 |
|------|--------|----------|
| `useFormat.test.js` | 12 | `formatBytes`（单位换算、空值处理）、`formatDate`（ISO 解析、空值）、`formatJson`（对象序列化、字符串透传）、`splitItems`（分隔、裁剪） |
| `useFilters.test.js` | 7 | 初始状态、关键词/状态/服务筛选、查询参数构建、标签生成、清空筛选 |
| `useUpload.test.js` | 4 | 初始文件列表、加载状态、文件选择、拖拽文件类型过滤、空文件阻止提交 |

### 示例：编写前端测试

```javascript
// frontend/src/__tests__/useFormat.test.js
import { describe, expect, it } from "vitest";
import { formatBytes } from "../composables/useFormat.js";

describe("formatBytes", () => {
  it("formats bytes correctly", () => {
    expect(formatBytes(1024)).toBe("1.0 KB");
  });
});
```

### 运行配置

```javascript
// frontend/vitest.config.js
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "happy-dom",
  },
});
```

## 性能基准测试

测试脚本：`tools/perf_benchmark.py`

测试流程：
1. 生成 10 万行（11.9 MB）日志文件
2. 逐项测试解析、写入、查询、统计、搜索耗时
3. 自动清理测试数据

需要在 Docker 环境下运行（依赖 PostgreSQL）。

## 手动测试清单

除了自动化测试外，以下场景建议手动验证：

### 上传

- [ ] 上传 `.log` 文件 → 成功
- [ ] 上传 `.txt` 文件 → 成功
- [ ] 上传 `.pdf` 文件 → 报错「不支持的文件类型」
- [ ] 上传空文件 → 报错「文件为空」
- [ ] 上传 > 10MB 文件 → 报错「文件过大」
- [ ] 拖拽上传（含非文本文件，如 .png）→ 自动过滤

### 认证

- [ ] 注册 → 成功
- [ ] 重复邮箱注册 → 报错
- [ ] 登录 → 成功，跳转工作台
- [ ] 错误密码 → 报错
- [ ] 关闭浏览器后重新打开 → 自动恢复登录态（Refresh Token）
- [ ] 退出 → 返回登录页

### 筛选与搜索

- [ ] 关键词筛选 → 列表和详情页过滤
- [ ] 状态筛选 → 过滤 parsed/analyzed
- [ ] 服务筛选 → 过滤匹配服务名的日志
- [ ] 搜索高亮 → 关键词在日志条目中黄色标记

### AI 分析

- [ ] 未配置 API Key → 按钮禁用，提示「AI 未配置」
- [ ] 点击分析 → 按钮显示「排队中」→「分析中」→ 完成
- [ ] 分析完成 → 显示摘要、异常原因、排障建议
- [ ] 分析历史 → 点击历史记录切换显示
- [ ] 分析失败 → 显示错误提示

### 排障面板

- [ ] 诊断指标（风险等级、关键事件数、异常占比）
- [ ] 高频异常统计
- [ ] 关键信息聚合（服务、请求链路、关键词）
- [ ] 级别分布柱状图
- [ ] 服务分布柱状图
- [ ] 关键事件时间线
