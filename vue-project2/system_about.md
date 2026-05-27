# 系统说明（system_about）

本文档用于毕设答辩复习：按**前端（Vue）**与**后端（Django）**两部分，介绍本项目实际用到的技术点、目录结构、核心业务流程、关键代码位置与易被提问的点。  
适用仓库：
- 前端：`E:\ResourceSharingPlatform\vue-project2`
- 后端：`E:\ResourceSharingPlatform\DjangoProject\DjangoProject01`

---

## 1. 项目总体架构与数据流

### 1.1 架构
- **前端**：Vue 3 + Vue Router + Axios + Vite（开发代理到 Django）
- **后端**：Django 6（函数式 API）+ MySQL + 自定义用户模型 + Token（`AuthToken`）鉴权
- **文件存储**：Django `MEDIA_ROOT` 本地磁盘保存图片（资源封面、头像、作品）

### 1.2 请求数据流（典型）
1. 用户在前端操作（登录/下单/评论等）
2. Axios 通过 `src/api/client.js` 发起请求
3. 请求拦截器自动注入 `Authorization: Bearer <token>`（若已登录）
4. Django 在 `users/api.py` 中解析 header，查 `AuthToken` 得到用户对象并做权限判断
5. 返回 JSON 结构：`{ ok: boolean, message: string, data: any }`

---

## 2. 前端（Vue）技术与代码结构

### 2.1 技术栈（来自 `package.json`）
- **Vue 3**：组合式 API（`ref/reactive/computed/onMounted` 等）
- **Vue Router 4**：前端路由与权限拦截
- **Axios**：HTTP 请求与拦截器
- **Vite**：开发服务器、构建、代理
- **Bootstrap**：依赖存在（`bootstrap`），但本项目 UI 主要是各页面的 `scoped` CSS（渐变/圆角/弹窗）

### 2.2 Vite 配置与代理（`vite.config.js`）
开发环境通过代理解决跨域：
- `/api` → `http://127.0.0.1:8000`
- `/images`、`/media` → `http://127.0.0.1:8000`

意义：
- 前端开发时请求仍写 `/api/...`，由 Vite 转发到 Django；
- 图片 URL 以 `/images/...` 访问也能正确代理到 Django 的 `MEDIA_URL`。

### 2.3 应用入口
- `src/main.js`：创建应用、挂载 Router、加载全局样式
- `src/App.vue`：应用根组件（RouterView 容器）

### 2.4 路由与权限（`src/router/index.js`）
关键点：
- 除 `/auth` 外默认需要登录（未登录重定向到登录页，并携带 `redirect`）
- 管理员页面使用 `meta.requiresAdmin`
- 管理员账号在前端会隐藏「收藏」入口

可答辩解释：
- 这是**前端拦截**，真正安全还需要后端 `_require_admin` 二次校验（本项目后端已做）。

### 2.5 会话存储（`src/utils/session.js`）
- 用 `localStorage` 保存：`{ token, user, role }`
- 登录成功 `setSession(...)` 会触发 `window.dispatchEvent('session-changed')`，用于同页响应式刷新（如顶部头像）
- 退出或 401 时 `clearSession()` 清除

### 2.6 Axios 封装（`src/api/client.js`）
做了两件关键事：
- **请求拦截**：若存在 session token，则自动设置 `Authorization` header
- **响应拦截**：遇到 **401** 自动清 session，并把后端 `message` 映射到 `err.message`

这会影响页面逻辑（答辩常问点）：
- Django 登录失败返回 401 会进入 Axios 的 `catch` 分支，页面若想统计登录失败次数，需要在 `catch` 里处理（已在 `AuthView.vue` 做了）。

### 2.7 API 模块划分（例）
项目采用“按业务拆分 API 文件”的方式（便于答辩展示结构化）：
- `src/api/auth.js`：注册/登录/登出
- `src/api/products.js`：资源（Equipment）公开列表、个人资源等
- `src/api/orders.js`：订单 checkout、确认交接/归还、提前归还/按时归还、删除订单
- `src/api/admin.js`：管理员用户/资源管理（禁用、删除、重置密码等）
- `src/api/works.js`：作品广场 + 评论 + 管理员审核/评论管理

### 2.8 组合式逻辑（Composables）
- `src/composables/useCart.js`：购物车逻辑（localStorage 持久化、计算合计、checkout payload）
  - 重要：`payloadForCheckout()` 只发送 `equipment_id + rental_days`，后端以数据库商品信息计算金额与租售类型，防篡改。

### 2.9 主要页面（Views）与功能对应
（答辩建议把“页面→接口→后端函数”串起来讲）
- `AuthView.vue`：登录/注册；登录错误超过 3 次提示联系管理员重置
- `HomeView.vue`：公开商品列表、详情弹窗、加入购物车、结算下单
- `OrdersView.vue`：订单管理（用户：买/卖两列；管理员：全站订单）
  - 租赁订单倒计时：展示“剩余时间：xx天xx小时”
  - 提前归还：双方确认后进入待归还，再双方确认归还完成
  - 按时归还：到期前 6 小时窗口内可发起
- `MyResourcesView.vue`：发布/编辑/下架/删除/重新提交审核
- `FavoritesView.vue`：收藏管理
- `WorksSquareView.vue`：作品广场（发布作品、评论弹窗、评论数量）
- `AdminResourcesView.vue`：资源审核/上下架/删除 + 状态筛选
- `AdminWorksView.vue`：作品审核/下架/删除 + 状态筛选
- `AdminWorkCommentsView.vue`：评论审核与管理（通过/驳回/删除）
- `UserManagementView.vue`：用户管理（禁用/启用/删除/重置密码为 123）

---

## 3. 后端（Django）技术与代码结构

### 3.1 技术栈与关键组件
- **Django 6.0.x**
- **数据库**：MySQL（`settings.py` 中 `DATABASES` 配置）
- **跨域**：`django-cors-headers`（`corsheaders` 中间件与允许源）
- **自定义用户模型**：`AUTH_USER_MODEL = 'users.User'`
- **鉴权方式**：简易 Token 表 `AuthToken`（非 JWT）
- **API 风格**：函数视图 + `JsonResponse`，统一返回 `{ok,message,data}`
- **文件上传**：头像/封面/作品使用 multipart；对大文件调整了 `DATA_UPLOAD_MAX_MEMORY_SIZE`

### 3.2 Django 项目入口与路由
- `djangoproject01/settings.py`：核心配置、MySQL、CORS、MEDIA、上传大小限制
- `djangoproject01/urls.py`：所有 API 路由定义（答辩可按业务模块讲）
- `users/api.py`：主要业务 API（资源/订单/作品/评论/管理员功能几乎都在这里）
- `users/models.py`：数据模型（User、Equipment、Order、OrderItem、RentalSchedule、PhotoWork、PhotoWorkComment 等）
- `users/migrations/`：迁移文件，记录模型演进（如新增 `buyer_return_ok`、提前归还标记、评论表）

### 3.3 统一返回结构与请求解析
- `_json_response(ok, data, message, status)`：统一响应
- `_get_json_body(request)`：读取 JSON body
- multipart 处理：
  - `_multipart_post_or_parse`：**POST** 优先使用 `request.POST/request.FILES`（流式，避免大文件触发 `DATA_UPLOAD_MAX_MEMORY_SIZE`）
  - PATCH/PUT 使用 `_parse_multipart`（读取 `request.body`，因此需要调大 `DATA_UPLOAD_MAX_MEMORY_SIZE`）

### 3.4 Token 鉴权与权限控制
关键函数：
- `_parse_auth_header`：解析 `Authorization`（兼容 `Bearer`/`Token`）
- `_get_user_by_token`：查 `AuthToken`
- `_require_user`：必须登录
- `_require_admin`：必须管理员

管理员判定：
- `_is_admin(user)`：role 为 `0/admin/管理员` 或 `is_superuser`

### 3.5 资源（Equipment）模块
关键点：
- `api_equipments_public`：只返回 **已上架** 的商品
- `api_equipment_create`：用户创建商品 → **待审核**
- `api_admin_equipments`：管理员查看全站商品，可按 `status` 筛选
- `api_admin_equipment_approve/off_shelf/delete`：审核通过/下架/删除（删除仅允许已下架）

租售类型一致性（答辩常问“为什么出售会走租赁”）：
- `_effective_listing_type(eq)`：当 `category` 为“出租/出售”时作为真源，避免 `listing_type` 脏数据导致流程串。

### 3.6 收藏（Favorite）模块
Favorite 使用外键关联 `Equipment`，并加了唯一约束（用户-商品唯一收藏）。

### 3.7 订单（Order）模块：出售/租赁状态机
核心常量：
- 租赁：`待取货` → `租赁中` → `待归还` → `已完成`
- 出售：`待交付` → `已完成`

关键流程点：
- `api_order_checkout`：下单创建 `Order` + 多条 `OrderItem`；订单类型由商品租售类型决定
- `api_order_confirm_handover_owner/buyer`：双方交接确认
  - 出售：双方确认后直接 `已完成`
  - 租赁：双方确认后生成 `RentalSchedule`，进入 `租赁中`
- `api_order_request_normal_return`：按时归还（到期前 6 小时窗口）
- `api_order_early_return`（买家）/`api_order_early_return_owner`（卖家）：提前归还双方确认
- `api_order_confirm_return_owner/buyer`：双方确认归还完成后 `已完成`
- `api_order_delete`/`api_admin_order_delete`：仅允许删除已完成订单（硬删除）

商品状态联动（用于答辩体现业务闭环）：
- 出售完成 → 商品自动 **已下架**
- 租赁开始（进入租赁中）→ 商品自动 **已下架**
- 租赁归还完成 → 商品自动 **待审核**（重新提交管理员上架审核）

### 3.8 作品广场（PhotoWork）与评论（PhotoWorkComment）
作品：
- `api_work_create`：用户发布作品，默认 `待审核`
- `api_works_public`：只返回 `已上架` 作品
- `api_admin_work_approve/off_shelf/delete`：管理员审核/下架/下架后删除

评论（先发后审）：
- `api_work_comments`：同一路径支持 `GET/POST`
  - GET：未登录只看 `已通过`；登录用户额外看“自己所有评论 + 已通过评论”
  - POST：评论创建，默认 `待审核`
- `api_work_comment_delete`：本人可删；管理员可删全部
- 管理员评论管理：
  - `api_admin_work_comments`：列表筛选（work_id/status）
  - `api_admin_work_comment_approve/reject/delete`

### 3.9 管理员用户管理
接口：
- `api_admin_users`：列表
- `api_admin_user_disable`：禁用/启用（禁用时清 token）
- `api_admin_user_delete`：删除
- `api_admin_user_reset_password`：重置密码为 `123` 并清 token

---

## 4. 核心业务流程（面向答辩讲解）

### 4.1 用户从浏览到下单（首页→购物车→订单）
1. 首页拉取 `/api/equipments`（仅已上架）
2. 打开详情，选择天数（出售固定 1）
3. 加入购物车（localStorage 保存）
4. 结算调用 `/api/orders/checkout`
5. 订单页展示买家订单（`/api/my/orders`）与卖家订单（`/api/my/sales-orders`）

### 4.2 出售订单
1. 下单 → `待交付`
2. 卖家确认交付 + 买家确认收货
3. 订单 → `已完成`
4. 商品 → `已下架`（自动）

### 4.3 租赁订单（含提前归还与按时归还）
1. 下单 → `待取货`
2. 双方确认取货（交接完成）→ 生成租期记录 → `租赁中`；商品自动下架
3. 归还路径：
   - 提前归还：买家确认 + 卖家确认 → 进入 `待归还`
   - 按时归还：到期前 6 小时窗口内，买卖任一方可发起 → 进入 `待归还`
4. 待归还：买家确认归还 + 卖家确认归还完成 → `已完成`
5. 商品 → `待审核`（自动重新提交管理员审核上架）

### 4.4 作品评论审核
1. 广场卡片点“评论”弹窗 → GET 拉评论
2. 发评论 → POST 创建 `待审核`
3. 管理员在“评论管理”通过后，对所有用户可见；作者始终可见自己的状态

---

## 5. 答辩高频提问点与建议回答

### 5.1 安全
- Q：为什么用 Token？  
  A：SPA 方便；后端可随时删除 token 强制下线。后续可加过期与刷新策略。
- Q：为什么很多接口 `csrf_exempt`？  
  A：请求不依赖 Cookie，靠 `Authorization`；生产环境仍建议加强 CSRF/限流/日志。
- Q：重置密码固定 123 是否安全？  
  A：演示版；真实应随机临时密码 + 强制首次登录修改或短信/邮箱验证。

### 5.2 状态机与一致性（最关键）
- Q：如何防止同一商品被多人同时下单（超卖）？  
  A：目前简化；可在下单时做“预占/锁定状态（reserved）”+ 超时释放；或库存机制/支付后扣减。
- Q：租赁到期如何计算？  
  A：约定到期 `contract_due_at` 用于归还窗口；`RentalSchedule` 用于租期事实记录与自动进入待归还，两者可在后续统一。

### 5.3 数据库设计
- Q：为什么 `OrderItem` 不用外键？  
  A：目前简化；外键能更好维护一致性、级联与查询，后续可改进并迁移数据。

### 5.4 性能与工程化
- Q：列表是否分页、是否 N+1？  
  A：目前通过 `[:500]` 限制；生产应分页与 `select_related/prefetch_related` 优化。

---

## 6. 建议的完善方向（加分项）
1. 商品“库存/锁定”避免超卖（订单预占 + 超时释放）
2. 订单超时机制（待取货/待交付超时自动取消并恢复商品状态）
3. 软删除与操作日志（订单/评论/资源）
4. 分页与搜索统一化（管理员模块）
5. 上传文件的 MIME/内容校验 + 对象存储/CDN

