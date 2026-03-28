# OpenClaw Skills 系统概述

> 来源：https://docs.openclaw.ai/skills  
> 抓取日期：2026-03-28

OpenClaw 使用 [AgentSkills](https://agentskills.io/) 兼容的 skill 文件夹来教会 Agent 使用工具。每个 skill 是一个包含 `SKILL.md` 文件（带 YAML frontmatter 和 Markdown 指令）的目录。

---

## Skill 加载位置与优先级

OpenClaw 按以下顺序加载 skill（优先级从高到低）：

| 位置 | 说明 |
|------|------|
| `/skills`（工作区） | 最高优先级，仅当前 agent |
| `/.agents/skills` | 项目级 agent skills |
| `~/.agents/skills` | 跨工作区的个人 agent skills |
| `~/.openclaw/skills` | 所有 agent 可用的共享 skills |
| 内置 skills | 随安装包附带 |
| `skills.load.extraDirs` | 自定义共享目录（最低优先级） |

同名 skill 以上表优先级覆盖。

---

## SKILL.md 格式

最简格式：

```markdown
---
name: image-lab
description: Generate or edit images via a provider-backed image workflow
---

# 指令正文
...
```

### 可选 frontmatter 字段

| 字段 | 说明 |
|------|------|
| `name` | 唯一标识符（snake_case），必填 |
| `description` | 显示给 agent 的一行描述，必填 |
| `homepage` | 显示为"Website"的 URL |
| `user-invocable` | `true/false`（默认 true），控制是否暴露为斜杠命令 |
| `disable-model-invocation` | `true/false`（默认 false），为 true 时不注入模型 prompt |
| `command-dispatch` | `tool`：斜杠命令直接调用工具而不经过模型 |
| `command-tool` | 配合 `command-dispatch: tool` 使用的工具名 |
| `metadata` | 单行 JSON，包含 `openclaw` 命名空间的加载门控配置 |

---

## 加载门控（Gating）

通过 `metadata` 字段控制 skill 在什么条件下加载：

```markdown
---
name: image-lab
description: Generate or edit images via a provider-backed image workflow
metadata:
  {
    "openclaw": {
      "requires": {
        "bins": ["uv"],
        "env": ["GEMINI_API_KEY"],
        "config": ["browser.enabled"]
      },
      "primaryEnv": "GEMINI_API_KEY"
    }
  }
---
```

### `metadata.openclaw` 字段说明

| 字段 | 说明 |
|------|------|
| `always: true` | 始终加载，跳过其他门控 |
| `emoji` | macOS Skills UI 显示的 emoji |
| `homepage` | macOS Skills UI 显示的链接 |
| `os` | 平台过滤，如 `["darwin", "win32"]` |
| `requires.bins` | PATH 上必须存在的可执行文件列表 |
| `requires.anyBins` | 至少一个存在即可 |
| `requires.env` | 必须存在的环境变量 |
| `requires.config` | `openclaw.json` 中必须为 truthy 的配置路径 |
| `primaryEnv` | 与 `skills.entries.*.apiKey` 关联的环境变量名 |
| `install` | 安装器规格（brew/node/go/download） |

---

## 本项目 SKILL.md 示例

本项目的 `SKILL.md`（`eink_push`）使用了以下门控：

```yaml
metadata:
  openclaw:
    requires:
      bins:
        - python
```

这意味着只有 `python` 在 PATH 上时，该 skill 才会被加载到 agent 的 prompt 中。

---

## Token 开销

每个 skill 注入到系统 prompt 的 XML 代价公式：

```
total_chars = 195 + Σ (97 + len(name) + len(description) + len(location))
```

粗估：每个 skill 约 24 tokens（不含字段长度）。

---

## ClawHub 公共注册表

- 浏览：https://clawhub.com
- 安装：`openclaw skills install <slug>`
- 更新：`openclaw skills update --all`

详见 [ClawHub 文档](./clawhub.md)。
