# 摄影资源分享平台（Resource Sharing Platform）

面向摄影器材与作品分享的 Web 应用：支持器材/设备的**出租与出售**、订单全流程、收藏、作品广场与评论审核，以及管理员后台（用户管理、资源/作品/评论审核、首页轮播与运营统计）。

采用前后端分离架构：**Vue 3** 单页应用 + **Django 6** REST 风格 JSON API + **MySQL** 持久化。

---

## 功能概览

| 模块 | 说明 |
|------|------|
| 用户 | 注册、登录（Token 鉴权）、个人资料、头像、实名相关字段 |
| 首页 | 公开商品列表、搜索、详情、购物车、下单结算、首页轮播展示 |
| 我的资源 | 发布/编辑器材，待审核 → 上架 → 下架/删除 |
| 订单 | 出售/租赁不同状态机；买卖双方确认交接与归还；提前归还、按时归还 |
| 收藏 | 收藏已上架商品 |
| 作品广场 | 发布摄影作品、评论（先发后审） |
| 管理后台 | 仪表盘统计、用户管理、商品/作品/评论审核、首页轮播配置 |

更详细的业务流程与答辩说明见：[vue-project2/system_about.md](vue-project2/system_about.md)。

---

## 技术栈与版本

### 前端（`vue-project2/`）

| 技术 | 版本 |
|------|------|
| Node.js | `^20.19.0` 或 `>=22.12.0`（见 `package.json` engines） |
| Vue | `^3.5.29` |
| Vue Router | `^4.6.4` |
| Vite | `^7.3.1` |
| Axios | `^1.14.0` |
| Bootstrap | `^5.3.8` |

### 后端（`DjangoProject01/`）

| 技术 | 版本 |
|------|------|
| Python | **3.12+**（Django 6 要求） |
| Django | **6.0.4** |
| django-cors-headers | **4.9.0** |
| mysqlclient | **2.2.8** |
| MySQL | **8.x**（推荐） |

### 开发与部署相关

| 说明 | 详情 |
|------|------|
| 本地开发服务器 | Django `runserver`（`:8000`）+ Vite dev（`:5173`） |
| 生产部署（可选） | Nginx + Gunicorn + 宝塔面板等 |
| 媒体文件 | 上传图片保存在 `DjangoProject01/images/`，URL 前缀 `/images/` |

---

## 项目结构

```
ResourceSharingPlatform/
├── DjangoProject01/          # Django 后端
│   ├── djangoproject01/      # 项目配置（settings、urls）
│   ├── users/                # 用户与业务模型、API（apis/）
│   ├── images/               # 上传图片（运行时目录，可按需初始化）
│   └── manage.py
├── vue-project2/             # Vue 3 前端
│   ├── src/
│   │   ├── api/              # 接口封装
│   │   ├── views/            # 页面
│   │   ├── router/           # 路由与权限
│   │   └── utils/            # 会话等工具
│   ├── vite.config.js        # 开发代理 /api、/images
│   └── package.json
└── README.md
```

---

## 环境准备

1. **Node.js** 20.19+ 或 22.12+
2. **Python** 3.12+
3. **MySQL** 8.x，创建数据库（默认库名 `sharingplatform`）
4. （Windows）安装 [MySQL 客户端开发库](https://dev.mysql.com/downloads/installer/) 以便编译 `mysqlclient`

---

## 本地运行

### 1. 数据库

在 MySQL 中创建数据库，例如：

```sql
CREATE DATABASE sharingplatform CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

在 `DjangoProject01/djangoproject01/settings.py` 中配置 `DATABASES`（默认示例）：

- 库名：`sharingplatform`
- 用户 / 密码：`root` / `root`
- 主机：`127.0.0.1:3306`

按本机环境修改即可。

### 2. 后端

```powershell
cd DjangoProject01
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install "Django>=6.0,<7" django-cors-headers mysqlclient
python manage.py migrate
python manage.py runserver
```

服务地址：**http://127.0.0.1:8000/**

> 请使用项目目录下的 `.venv`，不要误用系统 Anaconda 等未安装 Django 的 Python。

### 3. 前端

新开一个终端：

```powershell
cd vue-project2
npm install
npm run dev
```

浏览器访问：**http://localhost:5173**

开发环境下，Vite 会将 `/api`、`/images` 代理到 Django（见 `vite.config.js`），无需单独配置 `VITE_API_BASE_URL`。

### 4. 生产构建（可选）

```powershell
cd vue-project2
npm run build
```

构建产物在 `vue-project2/dist/`，需由 Nginx 等静态服务托管，并将 `/api/` 反代到 Gunicorn、`/images/` 指向 `DjangoProject01/images/`。

---

## API 约定

- 基础路径：`/api/...`
- 响应格式：`{ "ok": boolean, "message": string, "data": any }`
- 鉴权：登录后请求头 `Authorization: Bearer <token>`
- 跨域：开发时由 Vite 代理；后端通过 `django-cors-headers` 配置允许源（见 `settings.py`）

---

## 配置说明

| 文件 | 作用 |
|------|------|
| `DjangoProject01/djangoproject01/settings.py` | 数据库、CORS/CSRF、媒体路径、上传大小限制 |
| `DjangoProject01/djangoproject01/urls.py` | API 路由 |
| `vue-project2/vite.config.js` | 开发代理 |
| `vue-project2/src/api/client.js` | Axios 实例与 Token 拦截 |

本地默认 `ALLOWED_HOSTS` 为 `127.0.0.1`、`localhost`；部署到公网域名时需增加对应主机名及 HTTPS 的 `CSRF_TRUSTED_ORIGINS` / `CORS_ALLOWED_ORIGINS`。

---

## 注意事项

- `.venv/`、`node_modules/`、`dist/` 不应提交到 Git（已在各自 `.gitignore` 中忽略）。
- 请勿将生产环境的 `SECRET_KEY`、数据库密码提交到公开仓库。
- 管理员重置密码等能力为演示用途，生产环境应使用更安全的策略。
- 首次运行若页面无图，请确认 `DjangoProject01/images/` 中是否有数据，或通过前台上传生成。

---

## 许可证

本项目用于学习 / 毕设演示。如需开源协议，请自行添加 `LICENSE` 文件。
