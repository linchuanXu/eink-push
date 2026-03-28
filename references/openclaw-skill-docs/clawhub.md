# ClawHub 公共注册表

> 来源：https://docs.openclaw.ai/tools/clawhub  
> 抓取日期：2026-03-28

ClawHub 是 OpenClaw skills 和 plugins 的公共注册表。

- 网站：https://clawhub.com
- 用 `openclaw` 原生命令搜索/安装/更新 skills
- 需要发布/同步时，安装独立的 `clawhub` CLI

---

## 常用命令（原生 openclaw）

```bash
# 搜索
openclaw skills search "calendar"

# 安装
openclaw skills install <skill-slug>

# 更新全部
openclaw skills update --all
```

---

## 安装 clawhub CLI（发布/同步用）

```bash
npm i -g clawhub
# 或
pnpm add -g clawhub
```

---

## clawhub CLI 常用命令

### 认证

```bash
clawhub login           # 浏览器授权
clawhub login --token <token>
clawhub logout
clawhub whoami
```

### 搜索与安装

```bash
clawhub search "postgres backups"
clawhub install <skill-slug>
clawhub install <skill-slug> --version 1.2.0
```

### 更新

```bash
clawhub update <slug>
clawhub update --all
```

### 发布

```bash
clawhub publish ./my-skill \
  --slug my-skill \
  --name "My Skill" \
  --version 1.0.0 \
  --tags latest
```

### 批量同步（扫描本地 skills 并发布更新）

```bash
clawhub sync --all
clawhub sync --dry-run     # 预览，不实际上传
```

---

## 全局选项

| 选项 | 说明 |
|------|------|
| `--workdir <path>` | 工作目录（默认当前目录） |
| `--dir <path>` | Skills 子目录（默认 `skills`） |
| `--no-input` | 非交互模式 |

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `CLAWHUB_SITE` | 覆盖站点 URL |
| `CLAWHUB_REGISTRY` | 覆盖注册表 API URL |
| `CLAWHUB_CONFIG_PATH` | token/config 存储路径 |
| `CLAWHUB_WORKDIR` | 默认工作目录 |
| `CLAWHUB_DISABLE_TELEMETRY=1` | 禁用 sync 遥测 |

---

## 安全说明

- 任何人都可以发布 skill，但 GitHub 账号需至少注册满 1 周
- 收到 3+ 举报的 skill 会被自动隐藏
- **第三方 skill 视为不可信代码，启用前请先阅读源码**
