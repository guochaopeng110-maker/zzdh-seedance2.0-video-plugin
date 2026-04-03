---
quick_id: 260403-feb
type: quick-plan
mode: quick-full
name: 新增 README 文档与截图展示
objective: 为仓库新增 README，补充项目简介、安装、使用、FAQ，并确保两张截图在 Markdown 中可正确渲染。
files_modified: [README.md, .planning/STATE.md]
must_haves:
  - "README 必须包含项目简介、安装、使用、FAQ 四个核心板块"
  - "README 必须包含 docs/images/logs-windows.png 与 docs/images/plugin_menu.png 两张截图"
  - "图片路径必须使用相对路径并可在 Markdown 渲染"
  - "Quick task 必须写入 .planning/STATE.md 的 Quick Tasks Completed 表格"
---

# Quick Task 260403-feb - Plan

## Task 1

<task>
<name>创建 README 并补齐核心文档内容</name>
<files>
- README.md
</files>
<action>
新增根目录 README，包含项目简介、仓库结构、安装步骤、使用步骤与 FAQ；加入“插件菜单”和“日志窗口”两张截图，图片路径分别为 `docs/images/plugin_menu.png` 与 `docs/images/logs-windows.png`。
</action>
<verify>
`rg -n "项目简介|安装|使用|FAQ|docs/images/plugin_menu.png|docs/images/logs-windows.png" README.md`
</verify>
<done>README 可读、结构完整、图片路径可解析</done>
</task>

## Task 2

<task>
<name>执行 quick-full 验证并更新状态记录</name>
<files>
- .planning/STATE.md
- .planning/quick/260403-feb-readme-faq-docs-images-logs-windows-png-/260403-feb-SUMMARY.md
- .planning/quick/260403-feb-readme-faq-docs-images-logs-windows-png-/260403-feb-VERIFICATION.md
</files>
<action>
对 README 执行关键字与图片路径检查，写入 SUMMARY 与 VERIFICATION；在 `.planning/STATE.md` 新增 Quick Tasks Completed 表并追加当前任务记录，同时更新 Last activity。
</action>
<verify>
`rg -n "Quick Tasks Completed|260403-feb|Last activity:" .planning/STATE.md`
</verify>
<done>状态文件与 quick 产物齐全，且可追踪</done>
</task>
