# AI 中台管理系统

企业级后台中台基础框架 + 收入管理模块。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + ECharts |
| 后端 | Python FastAPI + SQLAlchemy 2.0 |
| 数据库 | SQLite（本地文件） |
| 认证 | JWT + bcrypt |
| 定时任务 | APScheduler（每日自动备份） |

## 快速启动

### 前置要求

- Python 3.10+
- Node.js 18+

### 一键启动（macOS / Linux）

```bash
./start.sh
```

启动后访问：
- 前端页面：http://localhost:5173
- 后端 API：http://127.0.0.1:8000
- API 文档：http://127.0.0.1:8000/api/docs

### 手动启动

**后端：**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端：**
```bash
cd frontend
npm install
npm run dev
```

## 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |

> **首次登录后请及时修改密码。**

## 目录结构

```
ai-platform/
├── backend/
│   ├── app/
│   │   ├── api/           # 路由层
│   │   ├── core/          # 配置、安全、调度
│   │   ├── models/        # ORM 模型
│   │   ├── schemas/       # Pydantic 校验
│   │   ├── db.py          # 数据库连接
│   │   ├── deps.py        # 依赖注入
│   │   └── main.py        # 应用入口
│   ├── data/              # SQLite 数据库文件
│   ├── backups/           # 自动备份目录
│   └── requirements.txt
│
└── frontend/
    └── src/
        ├── api/           # Axios 封装 + 接口定义
        ├── stores/        # Pinia 状态管理
        ├── router/        # 路由 + 权限守卫
        ├── layouts/       # 主布局
        └── views/         # 页面组件
            ├── Login.vue
            └── income/
                ├── Dashboard.vue  # 图表概览
                ├── Records.vue    # 收入记录管理
                └── Sources.vue    # 来源管理
```

## 数据备份

- 每天凌晨 2:00 自动将 `data/ai_platform.db` 备份到 `backups/` 目录
- 自动保留最近 7 天，超期自动删除
- 管理员可通过 `POST /api/backup/trigger` 手动触发备份

## 扩展新模块

1. 在 `backend/app/api/` 下新建模块目录
2. 在 `backend/app/main.py` 中注册路由
3. 在 `frontend/src/router/index.ts` 中添加路由配置
4. 在 `frontend/src/layouts/MainLayout.vue` 侧边栏中添加菜单项
