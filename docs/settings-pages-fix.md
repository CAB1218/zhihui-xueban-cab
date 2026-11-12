# 设置类页面修复说明（个人设置 / 偏好设置 / 帮助中心）

> 修复时间：2026-11-12
> 现象：右上角头像下拉的「个人设置 / 偏好设置 / 帮助中心」三个入口点开后都是 404（`/profile`、`/preferences`、`/help` 没有对应路由）

## 1. 原因

`components/layout/Header.vue` 的菜单直接 `router.push('/profile' | '/preferences' | '/help')`，
但路由表里只有场景前缀下的 `/scene/:sceneType/help`，另外两个页面根本不存在，于是落到 `NotFound`。

## 2. 修复内容

### 2.1 新增路由（不依赖场景前缀）

`src/router/routes/common-routes.ts`：

| 路径 | 名称 | 组件 |
|---|---|---|
| `/profile` | `ProfileSettings` | `views/user/ProfileSettingsView.vue` |
| `/preferences` | `PreferenceSettings` | `views/user/PreferenceSettingsView.vue` |
| `/help` | `HelpCenterStandalone` | 复用 `views/help/HelpCenterView.vue` |

三条都用 `AppLayout`（侧边栏 + 顶栏）包裹，`requiresAuth: true`，角色不限。
`Header.vue` 改为按路由名跳转，避免以后路径调整再次点空。

### 2.2 个人设置（`/profile`）

- 资料编辑：昵称、头像链接、手机号、年级、学校、专业、个人简介（昵称 2-50、头像需合法 URL、手机号格式校验）
- 头像实时预览（无链接时显示昵称首字）
- 右侧「账号信息」：邮箱（只读）、角色、租户、注册时间
- 「修改密码」：旧密码 + 新密码 + 确认，6-50 位，两次一致校验
- 接口：`PUT /users/{id}`、`PUT /users/{id}/password`，保存后 `auth/me` 重新拉取，顶栏昵称/头像即时更新

### 2.3 偏好设置（`/preferences`）

| 设置项 | 效果 |
|---|---|
| 界面主题 | 浅色 / 深色 / 跟随系统，选中即时预览；`html.dark` 类 + element-plus dark css-vars + `styles/dark.scss` 覆盖 `--color-*` |
| 侧边栏默认折叠 | 进入页面时侧边栏是否收起（`AppLayout` 直接消费该偏好） |
| 默认进入的场景 | 课堂 / 自习 / 考前 / 讨论；首页 `/` 重定向读取该偏好，登录后直达对应仪表盘 |

存储两层：

1. 本地 `localStorage.user_preferences`（`stores/user.ts`，启动即读，避免闪白）
2. 账号级 `users.preferences`（`PUT /users/{id}/preferences`），`GET /auth/me` 现在会返回 `preferences` 字段，登录后自动回填，换设备一致

「恢复默认」= 浅色 + 侧边栏展开 + 课堂模式（需点保存生效）。

### 2.4 顺带修复：AppLayout 内容被侧边栏遮住

`AppLayout.vue` 的主区域缺少 `margin-left`，而侧边栏是 `position: fixed; width: 220px`，
导致教师区页面（`/teacher/*`）与新增的设置页左侧内容被盖住约 220px。
已补 `margin-left: 220px`（折叠时 64px，移动端 0），与 `SceneLayout` 保持一致。

## 3. 后端改动

| 文件 | 改动 |
|---|---|
| `app/schemas/auth.py` | `UserInfoResponse` 增加 `preferences: Dict[str, Any]` |
| `app/api/v1/auth.py` | `/auth/me` 解析 `users.preferences` JSON 后一并返回，解析失败按 null 处理 |

无需数据库迁移（复用 `users.preferences` text 列）。

## 4. 验证记录

- 三个入口点击后地址正确（`/profile`、`/preferences`、`/help`），页面正常渲染，无 404
- 个人设置保存：提示「个人资料已保存」，`auth/me` 数据同步
- 偏好设置：切深色 → `html.dark = true`；保存成功；刷新后按服务端偏好恢复为浅色
- `GET /auth/me` 返回 `preferences: { theme, locale, default_scene, sidebar_collapsed, show_buddy, notification_enabled }`
- 1440 / 820 两个视口均无横向溢出，控制台 0 报错
- 教师区 `/teacher`、`/teacher/ai-chat` 补 `margin-left` 后布局正常，无溢出
