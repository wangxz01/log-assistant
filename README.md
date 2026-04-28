# Log Assistant

这是一个用于智能日志分析助手的最小全栈应用。当前版本已经打通基础主链路：注册/登录、上传日志、保存文件、解析日志、查看列表和详情、按条件筛选。PostgreSQL 用于保存用户和日志数据，Redis 已接入 Docker Compose，方便后续扩展后台任务。

## 当前进度

已完成：

- FastAPI 后端应用入口和统一路由注册
- 健康检查接口：`GET /health`
- 真实注册和登录接口：`POST /auth/register`、`POST /auth/login`
- 用户表自动初始化、重复邮箱检查、密码最小长度校验、加盐密码哈希和数据库保存
- 登录时根据邮箱查询用户、校验密码并生成签名 access token
- 日志接口基于 Bearer token 识别当前用户，日志数据按账号隔离
- 真实日志上传：接收文件、保存文件、写入数据库并返回日志 ID
- 批量日志上传：前端可一次选择多个日志文件，后端逐个保存、解析并返回结果列表
- 前端支持点击选择或拖拽上传日志文件
- 日志列表和详情：按当前用户查询已上传日志，展示状态、上传时间、文件名、所属用户和解析统计
- 基础日志解析：提取时间戳、日志级别、内容，并识别 `ERROR` / `WARN` 等关键事件
- 日志检索和筛选：支持按关键词、级别、时间范围筛选
- 基于 Pydantic 的请求和响应 schema
- service 层实现认证、日志存储、日志解析和基础分析汇总
- PostgreSQL、Redis、API、前端的 Docker Compose 一键启动
- Vue 3 + Vite 前端，包含独立登录/注册页和登录后的日志工作台
- 登录页与主界面分离，登录后才进入日志工作台
- Vite `/api` 代理，前端通过代理访问 Docker Compose 中的后端服务
- 日志列表查询改为“填写条件 -> 点击查询”模式，并显示当前应用的筛选条件
- 日志上传支持单文件、多文件和拖拽上传
- 基础测试覆盖健康检查、认证、日志解析和账号隔离

暂未实现：

- 刷新 token、服务端 token 失效列表和完整会话管理
- Redis 队列、后台任务或异步分析流程
- 更深入的异常检测、聚合统计和 AI 分析
- 生产级前端路由、状态管理和更完整的界面细化
- 更完整的日志搜索体验，比如高亮命中内容、分页和更复杂的组合筛选
- 更深入的日志分析展示，比如图表、聚合视图和告警规则

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
assets/
  uploads/
tools/
  log_generator/
```

- `app/`：FastAPI 后端主应用
- `frontend/`：Vue 3 + Vite 测试前端
- `tests/`：后端自动化测试
- `assets/uploads/`：本地上传日志文件目录，已被 Git 忽略
- `tools/log_generator/`：批量生成测试日志文件的工具
- `docker-compose.yml`：本地一键启动 API、前端、PostgreSQL 和 Redis

## 接口列表

- `GET /health`
- `POST /auth/register`
- `POST /auth/login`
- `POST /logs/upload`
- `POST /logs/upload/batch`
- `GET /logs`
- `GET /logs/{id}`
- `POST /logs/{id}/analyze`

`GET /logs` 和 `GET /logs/{id}` 支持可选筛选参数：

- `keyword`
- `level`
- `start_time`
- `end_time`

## 使用 Docker Compose 启动

```bash
docker compose up --build
```

启动后：

- 前端页面：`http://localhost:5173`
- API 地址：`http://localhost:8000`
- 交互式接口文档：`http://localhost:8000/docs`

前端在 Docker Compose 中会通过 `/api` 代理访问 `api` 服务。

首次修改后端、前端或依赖时，建议使用 `--build` 重新构建镜像。

前端上传控件支持点击选择和拖拽上传。选择一个文件时调用 `POST /logs/upload`，选择多个文件时调用 `POST /logs/upload/batch`。

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

## 生成测试日志

项目提供了一个不依赖第三方库的日志生成脚本，可用于批量生成前端上传测试文件。

默认生成 5 个日志文件，每个文件 120 行：

```bash
python tools/log_generator/generate_logs.py
```

自定义文件数量、行数和输出目录：

```bash
python tools/log_generator/generate_logs.py --files 10 --lines 300 --output sample_logs
```

生成目录默认为 `sample_logs/`，该目录已被 Git 忽略。生成的日志包含时间戳、日志级别、服务名、请求 ID、用户 ID、耗时和模拟消息，可直接在前端上传。

## 备注

- 当前分析能力仍是基础版本，主要用于打通日志上传、解析、筛选和汇总链路。
- `app/core/config.py` 集中管理基于环境变量的配置。
- PostgreSQL 已用于用户注册、登录、日志元数据和日志解析结果存储；Redis 已接入但当前还没有被请求处理流程使用。
- 上传的日志文件保存在 `assets/uploads/`，Docker Compose 中使用 `uploaded_logs` volume 持久化。
- 后端不会保存明文密码；当前使用 PBKDF2-SHA256 加盐哈希。
- 前端不再预填测试密码，注册时使用浏览器的新密码输入模式，减少弱密码提示。
