# openclaw skills CLI 命令

> 来源：https://docs.openclaw.ai/cli/skills  
> 抓取日期：2026-03-28

`openclaw skills` 命令用于检查本地 skills 以及从 ClawHub 安装/更新。

---

## 命令列表

```bash
# 搜索 ClawHub
openclaw skills search "calendar"

# 安装（写入当前工作区 skills/ 目录）
openclaw skills install <slug>
openclaw skills install <slug> --version <version>

# 更新
openclaw skills update <slug>
openclaw skills update --all

# 列出本地可见 skills
openclaw skills list
openclaw skills list --eligible    # 只显示当前会话可用的

# 查看 skill 详情
openclaw skills info <name>

# 健康检查
openclaw skills check
```

---

## 说明

- `search` / `install` / `update` 直接操作 ClawHub，安装到工作区 `skills/` 目录
- `list` / `info` / `check` 检查当前工作区和配置可见的本地 skills
