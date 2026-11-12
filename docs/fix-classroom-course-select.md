# 课堂互动「所属课程」无法选择的修复

> 现象：教师账号进入「课堂互动 → 发起课堂」，点开「所属课程」下拉显示 **无数据**，课堂创建按钮点了也没反应。教师工作台同时显示「课程数 0 / 暂无课程」。

## 1. 根因

前端课程下拉调用的是 `GET /api/v1/teachers/courses`，而该接口只返回 `Course.teacher_id == 当前用户` 的课程：

```python
# 修复前 services/teacher_service.py
stmt = select(Course).where(
    and_(Course.tenant_id == tenant_id, Course.teacher_id == teacher_id, Course.is_active == True)
)
```

系统中的 4 门示例课程都挂在 `admin` 名下（`teacher_id=1`），教师账号（如 `CAB-2`，`id=16`）名下没有课程，于是：

- 下拉拿到空数组 → 显示「无数据」
- `createForm.course_id` 为空 → 后端 `ClassroomCreate.course_id` 是**必填**，请求被 422 拦下，前端看到的表现就是「点创建没反应」
- 工作台「我的课程」同样为空，课程数统计为 0

## 2. 修复内容

### 2.1 课程可见范围（后端）

`services/teacher_service.py`

- `list_courses` 改为返回**租户内全部启用课程**，本人课程排前面（`case` 排序），并新增 `owned` / `teacher_id` 字段区分归属；
- 工作台 `course_count`、`student_count` 同步改为租户口径，避免出现「卡片 0 门 / 列表 4 门」的自相矛盾。

> 语义变化：`/teachers/courses` 从「我的课程」变成「本租户可管理课程」。单校 / 单租户场景下教师本来就应该能看到同租户的课程；若要严格区分，前端可用 `owned` 标记做「我的 / 共享」分组。

### 2.2 课堂页课程选择（前端）

`views/scene/classroom/ClassroomRoomView.vue`

- 数据源改为 `GET /learning-advice/courses`（返回租户内全部课程，学生调用也不会 403），加载时带 loading，课程被删后自动回退到第一门；
- 下拉支持 `filterable` 搜索，选项右侧显示年级；
- 下拉空态提示「暂无课程，用下方按钮新建或导入」；
- 下拉底部新增两个入口：
  - **新建课程**：填名称（必填）+ 学科 / 年级（选填），创建后自动选中；同名课程直接选中已有课程；
  - **导入课程**：复用 `FileImportDialog`，支持 csv / xlsx 模板下载、逐行校验、失败行明细，导入完成后自动选中第一门新课；
- 创建课堂前增加校验：没选课程时提示「请先在所属课程里选择课程；没有课程可点下拉底部的『新建课程』」。

### 2.3 新建课程接口（后端）

`POST /api/v1/learning-advice/courses`

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | 是 | 课程名称，最长 100 字 |
| `subject` | 否 | 留空按课程名推断（`guess_subject`），猜不出记 `general` |
| `grade` | 否 | 留空记「未设置」 |
| `semester` | 否 | 留空按当前年月推断，如 `2026-fall` |

返回 `{ id, name, existed }`；同名课程已存在时返回已有课程并置 `existed=true`，不报错，保证前端总能拿到可用的 `course_id`。课程教师记为当前登录用户。

## 3. 验证记录（2026-11-12）

| 项 | 结果 |
|---|---|
| 教师账号 `CAB-2` 调 `/teachers/courses` | 修复前 `[]`，修复后返回 4 门（含 `owned=false`） |
| 教师账号调 `/learning-advice/courses` | 返回 4 门 |
| 教师账号创建课堂（`course_id=3`） | 成功，返回加入码 |
| `POST /learning-advice/courses` 新建 | 成功；同名再次提交返回 `existed=true` |
| UI：课程下拉 | 4 门课程 + 底部「新建课程 / 导入课程」，样式正常 |
| UI：新建课程「UI测试课程」 | 创建成功并自动选中 |
| UI：导入课程弹窗 | 模板下载、字段说明、拖拽区正常 |
| UI：创建课堂 | 进入房间，显示加入码、参与者（教师）、举手表决/投票区域 |
| UI：教师工作台 | 课程数 4，列表显示四门课程，无「暂无课程」空态 |
| 控制台 | 0 个 JS 错误；1440 / 1024 无横向溢出 |
| 测试数据 | 测试课程、测试课堂（含参与者记录）已从数据库清理，课程仍为原 4 门 |
