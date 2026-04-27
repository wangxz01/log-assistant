# Log Assistant

这是一个用于智能日志分析助手的最小全栈脚手架。当前版本刻意保持简单：后端接口返回占位响应，前端用于测试和演示接口调用，PostgreSQL 和 Redis 已加入 Docker Compose，方便后续扩展持久化存储和后台任务。

## 当前进度

已完成：

- FastAPI 后端应用入口和统一路由注册
- 健康检查接口：`GET /health`
- 认证占位接口：`POST /auth/register`、`POST /auth/login`
- 日志占位接口：上传、列表、详情、触发分析
- 基于 Pydantic 的请求和响应 schema
- 简单 service 层，占位模拟认证、日志存储和分析状态
- PostgreSQL、Redis、API、前端的 Docker Compose 一键启动
- Vue 3 + Vite 初版前端，用于测试后端接口
- Vite `/api` 代理，前端通过代理访问 Docker Compose 中的后端服务
- 基础测试骨架和健康检查测试

暂未实现：

- 真实用户注册、登录、密码加密和鉴权
- 日志文件持久化和数据库写入
- Redis 队列、后台任务或异步分析流程
- 真正的日志解析、异常检测或 AI 分析
- 生产级前端路由、状态管理、权限控制和界面细化

## 项目结构

```text
app/
  api/
  core/
  models/
  schemas/
  services/
frontend/
  src/
tests/
```

- `app/`：FastAPI 后端主应用
- `frontend/`：Vue 3 + Vite 测试前端
- `tests/`：后端自动化测试
- `docker-compose.yml`：本地一键启动 API、前端、PostgreSQL 和 Redis

## 接口列表

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `POST /logs/upload`
- `GET /logs`
- `GET /logs/{id}`
- `POST /logs/{id}/analyze`

## 使用 Docker Compose 启动

```bash
docker compose up --build
```

启动后：

- 前端页面：`http://localhost:5173`
- API 地址：`http://localhost:8000`
- 交互式接口文档：`http://localhost:8000/docs`

前端在 Docker Compose 中会通过 `/api` 代理访问 `api` 服务。

## 本地启动

通常优先使用 Docker Compose。只有需要单独调试某一端时，再使用下面的本地启动方式。

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

前端开发服务器默认运行在 `http://localhost:5173`。开发环境下，前端会请求 `/api`，再由 Vite 代理到 `http://localhost:8000` 上的后端接口。

## 备注

- 业务逻辑目前是占位实现，便于在面试或学习场景中解释项目结构。
- `app/core/config.py` 集中管理基于环境变量的配置。
- PostgreSQL 和 Redis 已作为基础设施接入，但当前请求处理流程还没有真正依赖它们。
- `frontend/` 是一个 Vue 测试前端，用于验证当前后端接口，界面和交互后续还可以继续细化。
