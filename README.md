# Log Assistant

Log Assistant 是一个面向日志排障场景的智能分析平台。项目已经完成从账号体系、日志上传、日志解析、筛选检索，到异步 AI 分析和可视化排障面板的完整主链路。

当前版本适合用于课程项目、面试展示和后续功能扩展：代码结构清晰，功能边界明确，能够通过 Docker Compose 一条命令启动前端、后端、后台 Worker、PostgreSQL 和 Redis。

## 项目亮点

- **业务链路完整**：注册/登录 → 上传日志 → 解析日志 → 查看详情 → 异步分析 → 查看排障结果。
- **账号数据隔离**：日志按用户隔离，每个用户只能访问自己的日志和分析记录。
- **真实后端能力**：不是纯前端 demo，日志文件会保存到磁盘，元数据和解析结果会进入 PostgreSQL。
- **结构化解析结果**：日志行会解析出时间、级别、服务/模块名和内容，便于检索与统计。
- **异步分析流程**：分析任务提交后进入 Redis 队列，由独立 Worker 消费执行，前端轮询展示排队、分析中、完成、失败等状态。
- **AI 排障结果**：通过 DeepSeek API 生成摘要、异常原因和排障建议，结果以 JSON 数组存储，前端列表展示。
- **搜索命中高亮**：关键词筛选后，日志条目中命中文本自动高亮。
- **模块/服务筛选**：支持按服务/模块名筛选日志列表和日志详情。
- **统计图表**：排障面板展示级别分布和服务/模块分布的 CSS 柱状图。
- **上传安全校验**：文件大小限制、文件类型检查、空文件检测、编码异常检测。
- **统一错误处理**：全局异常捕获，前端友好错误提示。
- **展示型排障面板**：前端聚合高频异常、关键服务、请求链路、问题关键词和关键事件时间线，适合演示。
- **一键本地部署**：Docker Compose 同时启动 API、Worker、前端、PostgreSQL、Redis，开发环境支持热更新。
- **可复现演示数据**：提供 demo 数据脚本和截图，方便快速展示项目效果。
- **生产配置**：CORS、Cookie Secure、日志级别、上传限制均可通过环境变量配置。

## 界面预览

![排障面板](docs/images/troubleshooting-dashboard.png)

## 已完成功能

### 认证与权限

- 用户注册
- 用户登录
- 密码 PBKDF2-SHA256 加盐哈希
- JWT 鉴权
- HttpOnly Cookie 保存登录态，access token 过期后可通过 refresh token 自动续期
- 日志数据按账号隔离
- 其他用户访问日志详情或分析结果时返回 404
- Cookie Secure 可配置（通过 `COOKIE_SECURE` 环境变量）

### 日志管理

- 单文件上传
- 批量上传
- 拖拽上传
- 文件大小限制（默认 10 MB，通过 `MAX_UPLOAD_SIZE` 配置）
- 文件类型检查（默认 `.log` / `.txt`，通过 `ALLOWED_EXTENSIONS` 配置）
- 空文件检测
- 编码异常检测（非文本文件自动拒绝）
- 文件名防碰撞（UUID 前缀）
- 路径穿越防护（`Path().name` 提取）
- 文件保存到 `assets/uploads/`
- 数据库存储文件名、大小、状态、上传时间、所属用户
- 用户级日志编号：每个用户的日志从 `#1` 独立递增

### 日志解析与检索

- 提取时间戳
- 提取日志级别
- 提取服务/模块名：支持 `service=xxx`、`module=xxx`、`component=xxx`、`logger=xxx`、`app=xxx` 和 `[service]`
- 提取日志内容
- 识别 `ERROR`、`WARN`、`FATAL`、`CRITICAL` 等关键事件
- 日志列表支持按关键词、状态、服务/模块、时间范围筛选
- 日志详情支持按关键词、级别、服务/模块筛选
- 搜索命中高亮：关键词筛选后日志条目自动高亮匹配文本

### AI 分析

- `POST /logs/{id}/analyze` 提交真实分析任务
- Redis 保存任务状态：`pending`、`running`、`completed`、`failed`
- 独立 Worker 消费 Redis 队列并执行 AI 分析，避免 API 请求被长任务阻塞
- AI Key 未配置时，前端会显示明确提示并禁用分析按钮
- 分析完成后写入 `analysis_records`（causes/suggestions 存储为 JSONB）
- 前端实时轮询任务状态并刷新结果
- 支持查看历史分析记录

### 排障面板

- 高频异常统计
- 关键信息聚合：基于后端结构化的服务/模块字段、请求 ID 和问题关键词
- 统计图表：级别分布柱状图、服务/模块分布柱状图
- 关键事件时间线
- AI 摘要
- 异常原因（JSON 数组列表展示）
- 排障建议（JSON 数组列表展示）
- 分析历史回看

### 错误处理

- 全局异常捕获，统一 JSON 错误响应
- 上传失败：文件过大、类型不支持、空文件、非文本文件均有明确提示
- 分析失败：任务状态变为 `failed`，前端显示错误信息
- Token 失效：401 响应，前端提示重新登录
- Redis 不可用：Health Check 反映连接状态
- AI 接口异常：任务失败并记录错误原因

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11, FastAPI |
| 数据库 | PostgreSQL |
| 队列/状态 | Redis |
| 前端 | Vue 3, Vite |
| AI 分析 | DeepSeek API, OpenAI SDK |
| 测试 | pytest, Vitest |
| 数据库迁移 | Alembic |
| 部署 | Docker Compose |

## 快速开始

### 1. 配置环境变量

复制示例文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入 DeepSeek API Key。默认模型使用 `deepseek-v4-flash`：

```bash
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_MODEL=deepseek-v4-flash
REFRESH_TOKEN_EXPIRE_DAYS=14
```

不配置 API Key 时，注册、登录、上传、解析、列表、筛选、demo 数据仍可使用；前端会提示 AI 未配置，并禁用在线分析按钮。

### 2. 启动服务

```bash
docker compose up --build
```

启动后访问：

- 前端页面：`http://localhost:5173`
- API 地址：`http://localhost:8000`
- 接口文档：`http://localhost:8000/docs`

### 3. 使用流程

1. 注册账号并登录
2. 上传 `.log` 或 `.txt` 日志文件（最大 10 MB）
3. 在日志列表中按关键词、状态、服务/模块筛选
4. 进入日志详情页查看解析结果，搜索关键词自动高亮
5. 查看排障面板：级别分布、服务分布、高频异常、关键事件
6. 点击「分析」提交异步分析任务
7. 等待任务完成后查看 AI 摘要、异常原因和排障建议
8. 在分析历史中查看过往结果

## 生产配置

部署到生产环境时，建议修改以下环境变量：

```bash
# 安全密钥（必须修改）
AUTH_SECRET_KEY=<使用 openssl rand -hex 32 生成>

# HTTPS 环境
COOKIE_SECURE=true
CORS_ORIGINS=https://your-domain.com

# 日志级别
LOG_LEVEL=WARNING

# 上传限制
MAX_UPLOAD_SIZE=10485760
ALLOWED_EXTENSIONS=.log,.txt
```

使用反向代理（如 nginx）配置 HTTPS：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5173;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 演示数据

项目提供固定 demo 数据，适合课堂展示、面试讲解和截图复现。

先启动 Docker 服务，然后执行：

```bash
docker compose exec api python tools/demo_data/seed_demo_data.py
```

执行后使用以下账号登录：

- 邮箱：`demo@example.com`
- 密码：`demo12345`

脚本会重置这个 demo 账号，并写入一份已分析的结账链路故障日志。登录后进入日志详情页，可以直接查看排障面板、分析历史和原始日志片段。

## 生成测试日志

```bash
# 默认生成 5 个文件，每个 120 行
python tools/log_generator/generate_logs.py

# 自定义数量和行数
python tools/log_generator/generate_logs.py --files 10 --lines 300 --output sample_logs
```

生成的日志包含时间戳、级别、服务名、请求 ID 等字段，可直接上传测试。

## 本地开发

后端：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

前端：

```bash
cd frontend
npm install
npm run dev
npm test
```

Docker 开发模式已挂载源码并开启热更新：

- 后端：uvicorn `--reload` 检测 `app/` 下文件变动并重启
- Worker：`python -m app.worker` 独立消费 Redis 分析队列
- 前端：Vite HMR 热更新 `frontend/src/` 下组件
- 数据库：API 容器启动前自动执行 `alembic upgrade head`
- 工具脚本：`tools/` 已挂载到 API 容器，demo 数据脚本可直接执行

## 数据库迁移

项目使用 Alembic 管理 PostgreSQL 表结构。

Docker 启动时会自动执行：

```bash
alembic upgrade head
```

本地开发也可以手动执行：

```bash
alembic upgrade head
```

如果你的本地数据库是在引入 Alembic 之前创建的，表结构已经存在但没有迁移版本记录，可以先标记当前版本：

```bash
alembic stamp head
```

之后再使用 `alembic upgrade head` 管理后续结构变更。

## 项目结构

```text
app/
  api/routes/       路由：auth, health, logs
  core/             配置、数据库、安全
  models/           数据模型
  schemas/          请求/响应 schema
  services/         业务逻辑：认证、日志、AI 分析、任务状态
  worker.py         独立后台 Worker，消费 Redis 分析任务
frontend/
  src/
    composables/    可复用逻辑：useApi, useAuth, useFilters, useUpload, useFormat
    __tests__/      前端单元测试（Vitest）
tests/              后端自动化测试
tools/
  demo_data/        演示数据脚本
  log_generator/    测试日志生成器
docs/
  images/           README 展示截图
```

## API 列表

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查（含 Redis 连接状态） |
| `POST` | `/auth/register` | 注册 |
| `POST` | `/auth/login` | 登录 |
| `POST` | `/auth/refresh` | 刷新 Token |
| `POST` | `/auth/logout` | 登出 |
| `GET` | `/auth/me` | 当前用户信息 |
| `POST` | `/logs/upload` | 上传单个日志 |
| `POST` | `/logs/upload/batch` | 批量上传日志 |
| `GET` | `/logs` | 日志列表，支持 `keyword`、`status`、`service`、`start_time`、`end_time` |
| `GET` | `/logs/{id}` | 日志详情，支持 `keyword`、`level`、`service`、`page`、`per_page` |
| `POST` | `/logs/{id}/analyze` | 提交 AI 分析任务 |
| `GET` | `/logs/{id}/analyze/status` | 查询分析任务进度和结果 |
| `GET` | `/logs/{id}/analyses` | 查看分析历史记录 |
| `GET` | `/logs/{id}/stats` | 查看统计信息（级别分布、服务分布） |

## 当前完成度

| 里程碑 | 状态 | 说明 |
|--------|------|------|
| 日志上传与解析 | 已完成 | 文件保存、数据库记录、解析时间戳/级别/服务模块/内容 |
| 日志列表与详情 | 已完成 | 支持账号隔离、列表筛选、详情查看、搜索高亮 |
| 真实注册登录 | 已完成 | 用户表、重复邮箱检查、密码哈希、JWT、Cookie 会话恢复、refresh token 续期 |
| AI 分析 | 已完成 | 摘要、异常原因、排障建议、历史记录、AI Key 缺失提示、JSONB 结构化存储 |
| 异步分析 | 已完成 | Redis 队列、独立 Worker、任务状态、前端轮询 |
| 展示型结果页 | 已完成 | 高频异常、关键信息聚合、关键事件、统计图表、截图 |
| 上传安全 | 已完成 | 文件大小/类型限制、空文件检测、编码检测、路径穿越防护 |
| 统一错误处理 | 已完成 | 全局异常捕获、一致错误响应、前端友好提示 |
| 生产配置 | 已完成 | CORS/Cookie/日志级别可配置、反向代理示例 |
| 数据库迁移 | 已完成 | Alembic 管理表结构，Docker 启动自动迁移 |
| 前端测试 | 已完成 | Vitest 23 个测试用例覆盖 composables |
| 后端测试 | 已完成 | pytest 15 个测试用例覆盖核心逻辑 |

## 性能基准测试

使用 10 万行（11.9 MB）日志文件进行基准测试，测试环境为 Docker Compose 默认配置（PostgreSQL 16 / Redis 7 / Python 3.11）。

```bash
docker compose exec api python tools/perf_benchmark.py
```

### 测试结果

| 测试项 | 耗时 | 说明 |
|--------|------|------|
| 解析 10 万行日志 | 0.33s | 正则提取时间戳、级别、服务名、内容 |
| 写入 10 万条到 PostgreSQL | 4.66s | INSERT 100k 条 log_entries |
| 分页查询（第 1000 页） | 0.04s | OFFSET/LIMIT 分页，50 条/页 |
| 统计聚合（级别/服务/趋势） | 0.09s | GROUP BY 聚合，包含趋势时间桶 |
| 日志列表查询 | 0.006s | 单用户日志列表 |
| 关键词搜索（ILIKE） | 0.08s | 在 10 万条中模糊搜索，命中 20325 条 |
| **端到端总耗时** | **5.22s** | 解析 + 写入 + 查询 |

### 说明

- 10 万行日志从上传到可检索约 5 秒，其中写入数据库占 90% 时间。
- 查询和统计聚合均在 100ms 以内，前端交互无明显延迟。
- 测试脚本位于 `tools/perf_benchmark.py`，可直接复现。

## 待完善方向

- 日志搜索增强：复杂组合筛选、正则搜索。
- 分析面板继续增加趋势图、告警规则。
- 前端组件化拆分（从单文件拆分为 .vue 页面组件）。

## 验证

当前版本已通过：

```bash
# 后端测试
pytest -q

# 前端测试
cd frontend
npm test

# 前端构建
npm run build
```

## 备注

- `app/core/config.py` 集中管理基于环境变量的配置。
- PostgreSQL 存储用户、日志元数据、解析结果和分析记录（causes/suggestions 为 JSONB）。
- Redis 用于异步分析任务队列和状态管理，任务状态默认保留 24 小时。
- 上传文件保存在 `assets/uploads/`，Docker Compose 中使用 volume 持久化。
- AI 分析通过 DeepSeek API 实现，使用 OpenAI SDK 调用。
- 上传限制：默认 10 MB，仅支持 `.log` 和 `.txt` 文件。
