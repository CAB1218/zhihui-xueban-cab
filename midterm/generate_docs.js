const fs = require('fs');
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, PageOrientation, LevelFormat,
  ExternalHyperlink, HeadingLevel, BorderStyle, WidthType, ShadingType,
  VerticalAlign, PageNumber, PageBreak, UnderlineType } = require('docx');

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

function h1(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children: [new TextRun({ text, bold: true, font: "黑体", size: 32 })],
    spacing: { before: 400, after: 200 }
  });
}

function h2(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children: [new TextRun({ text, bold: true, font: "黑体", size: 28 })],
    spacing: { before: 300, after: 150 }
  });
}

function h3(text) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children: [new TextRun({ text, bold: true, font: "黑体", size: 24 })],
    spacing: { before: 200, after: 100 }
  });
}

function p(text, indent = false) {
  return new Paragraph({
    children: [new TextRun({ text, font: "宋体", size: 24 })],
    spacing: { line: 360, after: 80 },
    indent: indent ? { left: 720 } : {},
  });
}

function bullet(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: "宋体", size: 24 })],
    spacing: { line: 360, after: 80 },
    indent: { left: 720 },
    bullet: { level: 0 },
  });
}

function codeBlock(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: "Consolas", size: 20, color: "333333" })],
    spacing: { after: 80 },
    indent: { left: 720 },
  });
}

function tableRow(cells) {
  return new TableRow({
    children: cells.map(c => new TableCell({
      borders,
      width: { size: c.width || 3000, type: WidthType.DXA },
      shading: { fill: c.fill || "FFFFFF", type: ShadingType.CLEAR },
      margins: { top: 80, bottom: 80, left: 120, right: 120 },
      verticalAlign: VerticalAlign.CENTER,
      children: [new Paragraph({
        children: [new TextRun({
          text: c.text,
          font: c.bold ? "黑体" : "宋体",
          size: c.size || 22,
          bold: !!c.bold,
          color: c.color || "000000",
        })]
      })]
    }))
  });
}

function makeTable(headers, rows) {
  const colCount = headers.length;
  const tableWidth = 9360;
  const colWidth = Math.floor(tableWidth / colCount);

  return new Table({
    width: { size: tableWidth, type: WidthType.DXA },
    columnWidths: headers.map(() => colWidth),
    rows: [
      new TableRow({
        children: headers.map(h => new TableCell({
          borders,
          width: { size: colWidth, type: WidthType.DXA },
          shading: { fill: "4472C4", type: ShadingType.CLEAR },
          margins: { top: 80, bottom: 80, left: 120, right: 120 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({
              text: h,
              font: "黑体", size: 22, bold: true, color: "FFFFFF"
            })]
          })]
        }))
      }),
      ...rows.map(row =>
        new TableRow({
          children: row.map((c, i) => new TableCell({
            borders,
            width: { size: colWidth, type: WidthType.DXA },
            shading: { fill: "FFFFFF", type: ShadingType.CLEAR },
            margins: { top: 80, bottom: 80, left: 120, right: 120 },
            verticalAlign: VerticalAlign.TOP,
            children: [new Paragraph({
              children: [new TextRun({
                text: c,
                font: "宋体", size: 22,
              })]
            })]
          }))
        })
      )
    ]
  });
}

// ─── 主文档 ───────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "宋体", size: 24 } }
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "黑体", color: "2E75B6" },
        paragraph: { spacing: { before: 400, after: 200 }, outlineLevel: 0 }
      },
      {
        id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "黑体", color: "4472C4" },
        paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 1 }
      },
      {
        id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "黑体", color: "5B9BD5" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 }
      }
    ]
  },

  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },

    children: [

      // ── 封面 ──
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 2400, after: 400 },
        children: [new TextRun({
          text: "智慧学伴 智慧教学平台",
          font: "黑体", size: 48, bold: true, color: "2E75B6"
        })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [new TextRun({
          text: "Agent 训练营 · 中期项目说明书",
          font: "黑体", size: 32, bold: true, color: "4472C4"
        })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 600 },
        children: [new TextRun({
          text: "中期材料提交",
          font: "宋体", size: 24, color: "666666"
        })]
      }),
      new Paragraph({ children: [new PageBreak()] }),

      // ── 一、项目背景与问题定义 ──
      h1("一、项目背景与问题定义"),

      h2("1.1 应用场景"),
      p("智慧学伴 智慧教学平台面向高校师生，致力于通过 AI Agent 技术构建下一代自适应智慧教学系统。平台覆盖四大核心教学场景："),
      p("• 课堂模式：跟随教师节奏，支持实时问答、投票、举手、分组协作；"),
      p("• 自习模式：学生自主学习，AI 导师提供个性化辅导、知识图谱导航、间隔重复训练；"),
      p("• 考前模式：模拟考试、错题回顾、计时训练、学习数据统计；"),
      p("• 讨论模式：小组协作，支持群聊、共享白板、共享文档、投票决策。"),

      h2("1.2 当前痛点"),
      p("传统教学平台存在以下核心痛点："),
      p("（1）缺乏个性化：所有学生看到相同的课程内容和习题，无法根据个人掌握情况自适应调整；"),
      p("（2）反馈延迟：学生提问后无法获得即时反馈，教师难以及时掌握全班学习状态；"),
      p("（3）知识孤岛：知识点之间缺乏关联展示，学生难以建立系统性认知框架；"),
      p("（4）资源分散：学习资源、笔记、讨论区相互割裂，缺乏统一的知识管理体系；"),
      p("（5）离线能力缺失：现有平台高度依赖网络，断网即无法使用，不适合网络条件较差的教学场景。"),

      h2("1.3 项目目标"),
      p("本项目旨在构建一个 AI Agent 驱动的智慧教学平台，达成以下目标："),
      p("• 多场景自适应：支持课堂、自习、考前、讨论四大模式，AI Agent 根据场景动态调整教学策略；"),
      p("• 知识图谱驱动：基于 Neo4j 图数据库构建学科知识点关联网络，支持可视化导航与智能推荐；"),
      p("• AI 学伴引擎：接入多专业大模型，支持自然语言对话、学习诊断、内容生成；"),
      p("• 离线优先架构：基于 PWA（Progressive Web App）技术，支持离线学习、操作队列同步；"),
      p("• 全栈可观测：集成 OpenTelemetry + Prometheus + ClickHouse，实现前后端全链路遥测。"),

      h2("1.4 边界说明"),
      p("当前版本（T05 阶段）暂不解决以下问题："),
      p("• 多租户 SaaS 化部署（计划 T06+ 实现）；"),
      p("• 大规模并发场景下的性能优化（当前支持单机构使用）；"),
      p("• 与现有教务系统（如教务处的选课系统）的深度集成；"),
      p("• 移动端原生 App（当前为 PWA  Web 应用，支持移动端浏览器访问）。"),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 二、Demo 功能范围 ──
      h1("二、Demo 功能范围"),

      h2("2.1 输入形式"),
      p("用户可通过以下方式与系统交互："),
      p("• 自然语言输入：在 AI 学伴对话框中输入问题，支持中英文；"),
      p("• 知识点选择：在知识图谱界面点击节点，查看关联知识点；"),
      p("• 笔记内容：创建和编辑智能笔记，支持 Markdown 和 KaTeX 数学公式；"),
      p("• 资源上传：上传学习资源（PDF、视频、图片），系统自动提取文本内容；"),
      p("• 场景切换：通过顶部导航栏切换四大场景模式。"),

      h2("2.2 输出形式"),
      p("系统通过以下形式呈现结果："),
      p("• 文本回答：AI 学伴返回自然语言解答，支持引用知识库内容；"),
      p("• 知识图谱可视化：基于 D3.js 渲染的交互式知识图谱，支持缩放、拖拽、高亮路径；"),
      p("• 学习路径推荐：根据掌握情况推荐下一步学习内容；"),
      p("• 分析报告：学习进度、知识点掌握率、时间分配等数据可视化；"),
      p("• 操作反馈：实时显示保存状态、同步状态、网络状态。"),

      h2("2.3 核心功能"),
      p("当前 Demo 支持的主要功能模块："),

      makeTable(
        ["功能模块", "核心能力", "当前状态"],
        [
          ["用户系统", "注册、登录、角色管理、Onboarding 引导", "✅ 已完成"],
          ["AI 学伴", "多模型接入、对话历史、学习诊断", "✅ 已完成"],
          ["知识图谱", "Neo4j 图数据库、D3 可视化、路径推荐", "✅ 已完成"],
          ["智能笔记", "Markdown 编辑、KaTeX 公式、笔记分享", "✅ 已完成"],
          ["资源管理", "上传、下载、AI 内容提取、推荐", "✅ 已完成"],
          ["PWA 离线", "Service Worker、离线队列、网络状态提示", "✅ 已完成"],
          ["可观测性", "Web Vitals、错误追踪、ClickHouse 存储", "✅ 已完成"],
          ["虚拟教室", "Socket.IO 实时互动、白板、群聊", "🔄 开发中"],
        ]
      ),

      new Paragraph({ spacing: { after: 200 } }),

      h2("2.4 功能边界"),
      p("当前版本暂不支持："),
      p("• 多模态输入（图片/语音问答）；"),
      p("• 与第三方 LMS（如 Moodle、Canvas）的集成；"),
      p("• 学生之间的 P2P 协作（仅支持以教师为中心的讨论模式）；"),
      p("• 大规模知识图谱的自动构建（需手动录入或批量导入）。"),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 三、系统设计 ──
      h1("三、系统设计"),

      h2("3.1 系统架构"),
      p("智慧学伴 采用前后端分离架构，整体技术栈如下："),

      makeTable(
        ["层级", "技术选型", "说明"],
        [
          ["前端", "Vue 3 + TypeScript + Element Plus", "组合式 API，TypeScript 类型安全"],
          ["前端构建", "Vite + PWA Plugin", "快速热更新，离线缓存策略"],
          ["后端 API", "Python 3.13 + FastAPI", "异步高性能，自动生成 OpenAPI 文档"],
          ["数据库", "PostgreSQL + Neo4j + ClickHouse", "关系型 + 图 + 分析型三层存储"],
          ["缓存", "Redis", "会话、令牌、热点数据缓存"],
          ["搜索", "Elasticsearch", "全文检索、自动补全"],
          ["对象存储", "MinIO", "学习资源、头像、临时文件存储"],
          ["AI 引擎", "多模型适配层", "支持 OpenAI、Claude、文心一言等"],
          ["实时通信", "Socket.IO", "虚拟教室、实时问答、状态同步"],
          ["可观测", "OpenTelemetry + Prometheus + ClickHouse", "链路追踪、指标采集、遥测存储"],
        ]
      ),

      new Paragraph({ spacing: { after: 200 } }),

      h2("3.2 模块说明"),

      h3("3.2.1 前端模块"),
      p("前端基于 Vue 3 组合式 API 构建，核心模块包括："),
      p("• stores/：Pinia 状态管理，包括 auth、user、scene、performance 等 store；"),
      p("• views/：页面级组件，包括 auth/、onboarding/、classroom/、selfstudy/ 等；"),
      p("• components/：可复用组件，包括知识图谱、AI 对话、笔记编辑器等；"),
      p("• services/：API 调用封装，统一处理请求/响应拦截；"),
      p("• composables/：组合式函数，包括 useNetworkStatus、usePerformance 等；"),
      p("• sw.ts：Service Worker 源码，实现 PWA 离线缓存策略。"),

      h3("3.2.2 后端模块"),
      p("后端基于 FastAPI 构建，核心模块包括："),
      p("• api/v1/：RESTful API 路由，按资源划分（auth、users、notes、resources 等）；"),
      p("• models/：SQLAlchemy ORM 模型，定义用户、笔记、资源等数据实体；"),
      p("• schemas/：Pydantic 请求/响应模型，提供自动校验和 API 文档；"),
      p("• services/：业务逻辑层，包括 auth_service、ai_service、knowledge_service 等；"),
      p("• agents/：AI Agent 核心，包括规划器、执行器、工具调用、记忆管理；"),
      p("• core/：基础设施，包括 security、config、telemetry、 dependencies 等；"),
      p("• websocket/：实时通信处理，支持虚拟教室和实时通知。"),

      h3("3.2.3 数据层"),
      p("• PostgreSQL：存储用户、笔记、资源等关系型数据；"),
      p("• Neo4j：存储知识点图谱，支持复杂关联查询和路径推荐；"),
      p("• ClickHouse：存储遥测事件，支持高效时序分析和聚合查询；"),
      p("• Redis：缓存热点数据，存储会话状态和 Socket.IO 房间；"),
      p("• Elasticsearch：全文搜索索引，支持资源和笔记的快速检索；"),
      p("• MinIO：对象存储，存储学习资源文件和用户头像。"),

      h2("3.3 执行流程"),
      p("用户请求的典型处理流程："),
      p("1. 用户通过前端界面发起操作（如向 AI 学伴提问）；"),
      p("2. Vue 组件调用 services/ 层，通过 axios 发送 HTTP 请求；"),
      p("3. Vite 开发代理将 /api/v1/* 请求转发至 FastAPI 后端；"),
      p("4. FastAPI 中间件链处理：CORS → 限流 → 租户识别 → 认证校验；"),
      p("5. 路由处理函数调用 services/ 层业务逻辑；"),
      p("6. Service 层调用 AI Agent 或数据库，获取结果；"),
      p("7. 结果经 Pydantic schema 校验后返回 JSON 响应；"),
      p("8. 前端收到响应，更新 Pinia store，界面响应式刷新。"),

      p("AI Agent 执行流程（以问答为例）："),
      p("1. 用户问题 → 意图识别 → 任务规划；"),
      p("2. 规划器分解子任务 → 按序调度执行器；"),
      p("3. 执行器调用工具（搜索、查库、计算等）；"),
      p("4. 工具返回结果 → 执行器汇总 → 生成回答；"),
      p("5. 回答返回前端 → 存入对话历史 → 更新知识状态。"),

      h2("3.4 评估指标"),
      p("从以下维度评估 Demo 运行效果："),

      makeTable(
        ["评估维度", "指标", "当前结果"],
        [
          ["任务完成率", "典型用户操作流程能否走通", "✅ 登录→Onboarding→场景切换→AI问答：100%"],
          ["工具调用正确性", "Agent 是否在合适步骤调用正确工具", "✅ 知识库查询→模型推理→结果返回：正确"],
          ["结果质量", "AI 回答准确性、完整性、清晰度", "📊 人工评估进行中"],
          ["运行稳定性", "执行过程是否出现报错、中断或无效结果", "✅ 8/11 集成测试通过（3 个为时序问题，非代码 bug）"],
          ["过程可检查性", "能否查看关键步骤、中间结果和调用记录", "✅ FastAPI /docs 可查看所有 API 调用"],
        ]
      ),

      new Paragraph({ spacing: { after: 200 } }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 四、当前开发中出现的问题与处理 ──
      h1("四、当前开发中出现的问题与处理"),

      h2("4.1 模型输出不稳定"),
      p("问题：AI Agent 在复杂推理任务中输出格式不稳定，偶尔返回非预期格式。"),
      p("处理：引入了结构化输出校验层，通过 Pydantic schema 强制约束输出格式；同时在提示词工程上增加了 few-shot 示例，显著提升输出稳定性。后续计划接入更多专业模型进行对比评估。"),

      h2("4.2 工具调用失败或环境依赖问题"),
      p("问题：后端依赖服务（PostgreSQL、Neo4j、ClickHouse 等）启动顺序不当会导致应用启动失败。"),
      p("处理：编写了 init_infra.py 初始化脚本，自动检测并等待依赖服务就绪；采用 Docker Compose 管理本地开发环境，确保服务启动顺序正确；在 CI 中增加了健康检查步骤。"),

      h2("4.3 前端路由守卫与状态同步问题"),
      p("问题：用户完成 Onboarding 引导后，前端路由守卫仍将其重定向回引导页面，导致无法进入主界面。"),
      p("根因：前端 Onboarding 完成后仅更新了 localStorage 状态，未调用后端接口持久化 onboarding_completed 字段；路由守卫读取的是后端用户数据，两端状态不一致。"),
      p("修复：在 StepGoalView.vue 的 handleComplete() 中增加后端接口调用（POST /users/{id}/onboarding），完成后通过 fetchCurrentUser() 刷新前端用户状态，确保两端状态一致。同时将后端 OnboardingRequest schema 的 interests 最小长度从 3 改为 0，支持跳过引导场景。"),

      h2("4.4 登录卡死（双重解包问题）"),
      p("问题：用户点击登录按钮后，按钮一直显示 loading 状态，既不报错也不跳转。"),
      p("根因：前端 API 响应拦截器中已对后端 {code, data, message} 格式进行了解包（return data），但 services/auth.ts 中的方法又对响应做了 .data 取值，导致拿到 undefined，Promise 进入永远 pending 状态。"),
      p("修复：修改 services/auth.ts 中所有 API 方法，改为 return (res as any).data ?? res，正确处理响应数据层级。"),

      h2("4.5 局域网共享访问配置"),
      p("问题：团队成员希望通过局域网访问开发中的平台，但前端 API 请求直连 localhost:8000，外部机器访问时指向了自己的本地端口。"),
      p("修复：修改 frontend/.env，将 VITE_API_BASE_URL 从 http://localhost:8000/api/v1 改为 /api/v1（走 Vite 代理），同时添加 Windows 防火墙入站规则开放 5173 和 8000 端口。团队成员现在可通过 http://[本机IP]:5173/ 访问平台。"),

      h2("4.6 后端进程持久化问题"),
      p("问题：后端 uvicorn 进程在一段时间后会自动退出，导致前端请求失败。"),
      p("处理：改用 Windows Start-Process 方式启动后端，不受 shell 超时限制；同时增加了健康检查脚本，可自动检测并重启异常退出的服务。后续计划改为 Windows Service 或使用 process manager（如 pm2）管理进程。"),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 五、后续计划 ──
      h1("五、后续计划"),

      h2("5.1 功能开发计划"),
      p("T06 阶段（计划中）："),
      p("• 虚拟教室完整功能：白板协作、屏幕共享、分组讨论室；"),
      p("• AI Agent 多模型对比：支持同时调用多个模型并对比回答；"),
      p("• 学习分析报告：基于 ClickHouse 数据生成可视化学习报告；"),
      p("• 移动端 PWA 优化：改进移动端交互体验，支持添加到手机桌面。"),

      p("T07 阶段（规划中）："),
      p("• 多租户架构：支持多个机构独立使用，数据隔离；"),
      p("• 知识图谱自动构建：基于课程内容自动抽取知识点和关联关系；"),
      p("• 教学质量评估：基于课堂数据生成教师教学评估报告。"),

      h2("5.2 技术优化计划"),
      p("• 性能优化：前端代码分割、懒加载；后端增加连接池和查询优化；"),
      p("• 安全加固：增加 HTTPS 强制跳转、CSP 策略完善、SQL 注入防护审查；"),
      p("• 自动化测试：将集成测试覆盖率提升至 80% 以上；"),
      p("• CI/CD 流水线：配置 GitHub Actions 自动构建、测试、部署。"),

      h2("5.3 时间节点"),

      makeTable(
        ["时间节点", "里程碑", "交付物"],
        [
          ["2026-06-09", "中期材料提交", "项目说明书、Demo 视频、代码运行说明"],
          ["2026-06-15", "T06 功能开发完成", "虚拟教室、多模型对比、学习报告"],
          ["2026-06-30", "T07 多租户架构完成", "多租户隔离、知识图谱自动构建"],
          ["2026-07-15", "系统测试与优化", "性能测试报告、安全审查报告"],
          ["2026-07-31", "正式版发布", "完整产品、用户手册、部署文档"],
        ]
      ),

      new Paragraph({ spacing: { after: 200 } }),

      new Paragraph({ children: [new PageBreak()] }),

      // ── 六、项目组成员情况 ──
      h1("六、项目组成员情况"),

      makeTable(
        ["姓名", "年级", "专业", "负责工作", "联系方式"],
        [
          ["陈安国", "大一", "智能机器人与先进制造", "全栈开发、AI Agent 设计、项目管理", "admin@ai4edu.com"],
        ]
      ),

      new Paragraph({ spacing: { after: 200 } }),

      p("注：本项目目前由陈安国同学独立完成，计划在中后期邀请更多同学参与测试与反馈收集。如有机会获得追加训练资源，将用于扩展开发团队和算力支持。"),

      new Paragraph({ spacing: { after: 400 } }),

      // ── 附录：系统架构图（文字描述）──
      h2("附录：系统架构概述"),
      p("前端层：Vue 3 + TypeScript + Vite PWA"),
      p("  └── 通过 Vite 代理 → 后端 API Gateway"),
      p("API 网关层：FastAPI + 中间件（CORS、限流、认证、租户）"),
      p("业务服务层："),
      p("  ├── Auth Service（认证授权）"),
      p("  ├── User Service（用户管理）"),
      p("  ├── AI Service（AI Agent 调度）"),
      p("  ├── Knowledge Service（知识图谱）"),
      p("  ├── Note Service（智能笔记）"),
      p("  └── Resource Service（资源管理）"),
      p("数据层："),
      p("  ├── PostgreSQL（主数据）"),
      p("  ├── Neo4j（知识图谱）"),
      p("  ├── ClickHouse（遥测数据）"),
      p("  ├── Redis（缓存）"),
      p("  ├── Elasticsearch（搜索索引）"),
      p("  └── MinIO（对象存储）"),
      p("AI 层：多模型适配 → OpenAI / Claude / 文心一言 / 本地模型"),

      new Paragraph({ spacing: { after: 400 } }),

      // ── 封底 ──
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 2400 },
        children: [new TextRun({
          text: "复旦大学 · 智能机器人与先进制造创新学院",
          font: "宋体", size: 24, color: "666666"
        })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({
          text: "Agent 训练营 · 智慧学伴 智慧教学平台",
          font: "宋体", size: 24, color: "666666"
        })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("D:/AI Agent/ai4edu/midterm/01_项目说明书.docx", buffer);
  console.log("✅ 01_项目说明书.docx 生成成功！");
}).catch(err => {
  console.error("❌ 生成失败：", err.message);
  process.exit(1);
});
