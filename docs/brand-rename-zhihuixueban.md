# 品牌更名：AI4Edu → 智慧学伴

> 需求：登录页标题改为「智慧学伴智能体」，产品中所有对外显示的名称统一为「智慧学伴」。

## 1. 命名约定

| 场景 | 名称 |
|---|---|
| 产品名 / 侧边栏 / 安装名 | 智慧学伴 |
| 登录页主标题 | 智慧学伴智能体 |
| 登录页副标题 | AI 驱动的个性化学习体验 |
| 浏览器标签 | `页面名 - 智慧学伴`（无页面名时为「智慧学伴智能体」） |
| 帮助中心 / AI 自称 | 智慧学伴 |

英文环境（`en-US`）保留对应译名 `Smart Learning Companion`。

## 2. 改动清单

### 前端

| 文件 | 改动 |
|---|---|
| `src/views/auth/LoginView.vue` | 标题 `AI4Edu 智慧教学平台` → `智慧学伴智能体`；副标题间距调整；logo `alt` 改「智慧学伴」 |
| `src/views/auth/RegisterView.vue` | logo `alt` 改「智慧学伴」 |
| `src/components/layout/Sidebar.vue` | 侧边栏品牌文字 `AI4Edu` → `智慧学伴` |
| `src/router/guards.ts` | `document.title` 后缀与默认标题改「智慧学伴」 |
| `index.html` | `<title>智慧学伴 - 智能教学平台</title>` |
| `public/manifest.json` | `name` / `short_name` / `description` 更名 |
| `public/locales/zh-CN.json`、`en-US.json` | `common.appName` 更名 |
| `src/views/help/HelpCenterView.vue` | 3 条 FAQ 文案中的 AI4Edu → 智慧学伴 |
| `src/sw.ts` | 离线页标题、通知默认标题更名 |
| `public/favicon.svg` | 图标由 `AI` + `4Edu` 改为「智」+「学伴」 |
| `public/icons/*.png` | 8 个尺寸的 PWA 图标按新 SVG 重新渲染 |

### 后端

| 文件 | 改动 |
|---|---|
| `app/agents/*.py`（10 个 Agent） | system prompt 中「你是AI4Edu智慧教学平台…」→「你是「智慧学伴」智能体…」，让模型回答时自称智慧学伴 |
| `app/api/v1/help.py` | 帮助文章与 FAQ 文案更名 |
| `app/main.py` | OpenAPI 描述改为「智慧学伴智能体 API（AI 驱动的个性化学习与智慧教学平台）」 |

### 有意保留的部分

- `.env` 的 `APP_NAME=ai4edu`、健康检查 `service` 字段：技术标识，供容器与监控使用，改动会牵连部署脚本；
- 代码内部标识：`AI4EduDBSchema`（IndexedDB schema 名）、包名、目录名、数据库名、示例邮箱域名（`@ai4edu.com` 等）。**这些一旦改名会导致已有账号无法登录或本地数据丢失**，因此保持原样；
- 文件头注释里的「AI4Edu xxx组件」：不对外显示，未批量替换以缩小 diff。

## 3. 验证（2026-11-12）

| 项 | 结果 |
|---|---|
| 登录页标题 | `智慧学伴智能体` |
| 登录页副标题 | `AI 驱动的个性化学习体验` |
| 浏览器标签 | `登录 - 智慧学伴` / `场景仪表盘 - 智慧学伴` / `帮助中心 - 智慧学伴` / `个人设置 - 智慧学伴` |
| 侧边栏品牌 | 「智」图标 + `智慧学伴`，无换行、无溢出 |
| 帮助中心接口 | 返回「如何开始使用智慧学伴」等新文案 |
| PWA 图标 | 512px 渲染为「智 / 学伴」，居中无裁切 |
| 控制台 | 0 个 JS 错误 |

> 已登录用户如果看到旧标题，是 Service Worker 的离线缓存导致的，强制刷新（Ctrl/Cmd + Shift + R）或清除站点数据后即可更新。
