# Log Assistant

智能日志分析助手，支持日志上传、解析、筛选和 AI 分析。FastAPI 后端 + Vue 3 前端，PostgreSQL 存储，Docker Compose 一键部署。

## 功能

- 用户注册/登录，JWT 鉴权，日志数据按账号隔离
- 日志上传（单文件/批量/拖拽），自动解析时间戳、级别、内容
- 日志列表筛选（关键词、状态、时间范围）
- 用户级日志编号，每个用户的日志从 #1 独立递增
- AI 驱动的日志分析（调用 DeepSeek API），产出摘要、异常原因和排障建议
- 异步后台分析，基于 Redis 任务队列，前端实时轮询进度
- 分析历史记录，支持查看历次分析结果
- Docker Compose 一键启动（API、前端、PostgreSQL、Redis），开发环境热更新

## 快速开始

### 1. 配置环境变量

复制示例文件并填写 DeepSeek API Key：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```
DEEPSEEK_API_KEY=your-deepseek-api-key
```

> 不配置 API Key 时项目仍可正常启动，但 AI 分析功能不可用。

### 2. 启动服务

```bash
docker compose up --build
```

启动后访问：

- 前端页面：`http://localhost:5173`
- API 地址：`http://localhost:8000`
- 接口文档：`http://localhost:8000/docs`

### 3. 使用流程

1. 在登录页注册账号并登录
2. 在工作台上传日志文件（`.log` / `.txt`）
3. 在日志列表中按关键词、状态、时间筛选
4. 点击日志条目进入详情页
5. 点击「分析」按钮，任务提交到后台队列，前端实时显示进度（排队中 → 分析中）
6. 分析完成后自动展示摘要、异常原因（列表）和排障建议（列表）
7. 右侧面板可查看分析历史记录，点击可回顾

## 开发模式

容器已挂载源码并开启热更新，修改代码后无需重新构建：

- 后端：uvicorn `--reload` 检测 `app/` 下文件变动并重启
- 前端：Vite HMR 热更新 `frontend/src/` 下的组件

仅修改了 `requirements.txt` 或 `package.json` 时才需重新 `docker compose up --build`。

## 本地调试

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
```

## 生成测试日志

```bash
# 默认生成 5 个文件，每个 120 行
python tools/log_generator/generate_logs.py

# 自定义数量和行数
python tools/log_generator/generate_logs.py --files 10 --lines 300 --output sample_logs
```

生成的日志包含时间戳、级别、服务名、请求 ID 等字段，可直接上传测试。

## 项目结构

```text
app/
  api/routes/       路由：auth, health, logs
  core/             配置、数据库、安全
  models/           数据模型
  schemas/          请求/响应 schema
  services/         业务逻辑：认证、日志、AI 分析
frontend/
  src/              Vue 3 + Vite 前端
tests/              后端自动化测试
tools/
  log_generator/    测试日志生成器
```

## 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/auth/register` | 注册 |
| POST | `/auth/login` | 登录 |
| POST | `/logs/upload` | 上传单个日志 |
| POST | `/logs/upload/batch` | 批量上传日志 |
| GET | `/logs` | 日志列表（支持 keyword/status/start_time/end_time 筛选） |
| GET | `/logs/{id}` | 日志详情 |
| POST | `/logs/{id}/analyze` | 提交 AI 分析任务（异步） |
| GET | `/logs/{id}/analyze/status` | 查询分析任务进度和结果 |
| GET | `/logs/{id}/analyses` | 分析历史记录 |

## 备注

- `app/core/config.py` 集中管理基于环境变量的配置。
- PostgreSQL 存储用户、日志元数据、解析结果和分析记录。
- Redis 用于异步分析任务的状态管理（pending / running / completed / failed），任务结果保留 24 小时。
- 上传文件保存在 `assets/uploads/`，Docker Compose 中使用 volume 持久化。
- 密码使用 PBKDF2-SHA256 加盐哈希，不存储明文。
- AI 分析通过 DeepSeek API 实现，使用 OpenAI SDK 调用，后台线程执行不阻塞请求。
