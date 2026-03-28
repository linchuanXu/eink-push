# Skills 配置参考

> 来源：https://docs.openclaw.ai/tools/skills-config  
> 抓取日期：2026-03-28

所有 skills 配置在 `~/.openclaw/openclaw.json` 的 `skills` 字段下。

---

## 完整示例

```json5
{
  skills: {
    allowBundled: ["gemini", "peekaboo"],
    load: {
      extraDirs: ["~/Projects/agent-scripts/skills"],
      watch: true,
      watchDebounceMs: 250,
    },
    install: {
      preferBrew: true,
      nodeManager: "npm",  // npm | pnpm | yarn | bun
    },
    entries: {
      "image-lab": {
        enabled: true,
        apiKey: { source: "env", provider: "default", id: "GEMINI_API_KEY" },
        env: {
          GEMINI_API_KEY: "GEMINI_KEY_HERE",
        },
      },
      peekaboo: { enabled: true },
      sag: { enabled: false },
    },
  },
}
```

---

## 字段说明

### 顶层字段

| 字段 | 说明 |
|------|------|
| `allowBundled` | 内置 skill 白名单；设置后只有列表中的内置 skill 可用 |

### `load` 字段

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `extraDirs` | `[]` | 额外 skill 目录（最低优先级） |
| `watch` | `true` | 监听 skill 文件变化并热重载 |
| `watchDebounceMs` | `250` | 文件变化防抖时间（毫秒） |

### `install` 字段

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `preferBrew` | `true` | 优先使用 brew 安装器 |
| `nodeManager` | `npm` | Node 安装器类型（npm/pnpm/yarn/bun） |

### `entries.<skill-name>` 字段

| 字段 | 说明 |
|------|------|
| `enabled` | `false` 禁用该 skill（即使已安装） |
| `env` | 为 agent 运行注入的环境变量（不覆盖已有值） |
| `apiKey` | 快捷方式，对应 `primaryEnv` 声明的变量；支持明文字符串或 SecretRef 对象 |
| `config` | 自定义 per-skill 配置字段（必须放在这里） |

### SecretRef 格式

```json
{ "source": "env", "provider": "default", "id": "GEMINI_API_KEY" }
```

---

## 注意事项

- skill 名含连字符时，JSON5 中需要加引号：`"image-lab": { ... }`
- `env` 和 `apiKey` 只在 host 运行中生效；沙盒环境需要单独配置 `sandbox.docker.env`
- 配置变更在下一个 agent turn 或新会话开始时生效（watch 模式下热重载）
