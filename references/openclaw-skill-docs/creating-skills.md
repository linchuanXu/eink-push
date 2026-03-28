# 创建 Skills 指南

> 来源：https://docs.openclaw.ai/tools/creating-skills  
> 抓取日期：2026-03-28

Skills 告诉 agent 如何以及何时使用工具。每个 skill 是一个包含 `SKILL.md` 的目录，文件中有 YAML frontmatter 和 Markdown 指令。

---

## 快速创建

### 1. 创建 skill 目录

```bash
mkdir -p ~/.openclaw/workspace/skills/hello-world
```

### 2. 编写 SKILL.md

```markdown
---
name: hello_world
description: A simple skill that says hello.
---

# Hello World Skill

When the user asks for a greeting, use the `echo` tool to say
"Hello from your custom skill!".
```

### 3. 加载 skill

```bash
# 在对话中开新会话
/new

# 或重启 gateway
openclaw gateway restart
```

验证是否加载：

```bash
openclaw skills list
```

### 4. 测试

```bash
openclaw agent --message "give me a greeting"
```

---

## Skill 元数据参考

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 唯一标识符（snake_case） |
| `description` | 是 | 显示给 agent 的一行描述 |
| `metadata.openclaw.os` | 否 | 平台过滤，如 `["darwin"]` |
| `metadata.openclaw.requires.bins` | 否 | PATH 上必须存在的可执行文件 |
| `metadata.openclaw.requires.config` | 否 | 必须为 truthy 的配置键 |

---

## 最佳实践

- **简洁**：指令只说"做什么"，不用教 AI 怎么做 AI
- **安全**：使用 `exec` 的 skill 要防止不可信输入注入任意命令
- **本地测试**：`openclaw agent --message "..."` 先本地验证
- **ClawHub 分享**：发布到 https://clawhub.com 供社区使用

---

## Skill 位置汇总

| 位置 | 优先级 | 作用范围 |
|------|--------|---------|
| `<workspace>/skills/` | 最高 | 当前 agent |
| `~/.openclaw/skills/` | 中 | 所有 agent 共享 |
| 内置（随 OpenClaw 安装） | 最低 | 全局 |
| `skills.load.extraDirs` | 最低 | 自定义共享目录 |

---

## 相关文档

- [Skills 系统参考](./skills.md)
- [Skills 配置](./skills-config.md)
- [ClawHub 注册表](./clawhub.md)
