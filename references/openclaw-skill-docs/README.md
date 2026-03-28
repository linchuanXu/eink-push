# OpenClaw Skill 参考文档

从 https://docs.openclaw.ai 抓取，抓取日期：2026-03-28。

## 文件列表

| 文件 | 原始页面 | 内容 |
|------|---------|------|
| [skills.md](./skills.md) | `/skills` | Skill 系统概述：加载位置、优先级、格式、门控、token 开销 |
| [creating-skills.md](./creating-skills.md) | `/tools/creating-skills` | 创建 skill 的完整步骤与最佳实践 |
| [skills-config.md](./skills-config.md) | `/tools/skills-config` | `openclaw.json` 中 `skills.*` 配置参考 |
| [clawhub.md](./clawhub.md) | `/tools/clawhub` | ClawHub 注册表使用与 clawhub CLI 命令 |
| [cli-skills.md](./cli-skills.md) | `/cli/skills` | `openclaw skills` CLI 子命令速查 |

## 与本项目的关系

本项目的 `SKILL.md` 文件（根目录）是一个 OpenClaw AgentSkills 兼容的 skill，
教会 OpenClaw agent 将内容推送到阅星曈墨水屏设备。

关键字段：
- `name: eink_push`
- `requires.bins: [python]`（python 不在 PATH 时 skill 不加载）
