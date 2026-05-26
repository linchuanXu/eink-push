# skill-cleaner 使用指南与 eink-push 优化方案

> 依据：2026-05-26 查看 GitHub 上游
> [`steipete/agent-scripts/skills/skill-cleaner`](https://github.com/steipete/agent-scripts/tree/main/skills/skill-cleaner)。
> 该 Skill 的核心说明在
> [`SKILL.md`](https://raw.githubusercontent.com/steipete/agent-scripts/main/skills/skill-cleaner/SKILL.md)。

本文分两部分：

1. 如何使用 `skill-cleaner` 审计本机或项目中的 Skills。
2. 如何把 `eink-push` 优化成更稳定、更省上下文、更容易触发和维护的高质量 Skill。

---

## 1. skill-cleaner 是什么

`skill-cleaner` 是一个用于审计 Codex / OpenClaw Skills 的工具。它关注的不是某个 Skill 的业务逻辑，而是整个 Skill 集合对 Agent 的影响：

- 哪些 Skill 根目录被加载，哪些被配置禁用。
- 是否有同名 Skill、近似描述、近似正文造成重复。
- 哪些 Skill 最近没有被显式触发或读取，可能是未使用候选。
- 每个 Skill 描述会占用多少提示词预算。
- 哪些描述过长，可以压缩以节省上下文。

它特别适合在以下场景使用：

- 本机装了很多 Skills，Agent 启动提示越来越臃肿。
- 同一个 Skill 在系统目录、插件缓存、个人目录、项目目录里重复出现。
- 想知道一个 Skill 的 `description` 是否太长、是否容易误触发。
- 想清理废弃 Skill，但又不确定哪些真的没被用过。

---

## 2. 安装与运行方式

### 2.1 直接在 agent-scripts 仓库运行

```powershell
git clone https://github.com/steipete/agent-scripts.git
Set-Location agent-scripts
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --months 3
```

如果已经有这个仓库，进入仓库根目录后直接运行：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --months 3
```

上游文档写明：可以从 `skill-cleaner` Skill 目录或 `agent-scripts` 仓库根目录运行。

### 2.2 常用参数

只看 Skill 文件，不扫描日志：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --no-logs
```

扩大使用记录窗口到 6 个月：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --months 6
```

扫描更深的历史日志，适合大清理前使用：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --months 6 --max-log-mb 800 --deep-logs
```

按指定上下文窗口和预算比例估算 Skill 描述预算：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --context-tokens 272000 --budget-percent 2 --no-logs
```

额外扫描一个自定义 Skill 根目录：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --root "D:\path\to\skills" --no-logs
```

### 2.3 在 eink-push 维护场景中的推荐运行

如果目标是审计 `eink-push` 是否和本机其他 Skill 冲突，建议先跑轻量版：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --no-logs
```

如果目标是判断 `eink-push` 是否真的被触发、是否被其他同类 Skill 分流，再跑日志版：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --months 6 --deep-logs
```

如果 `eink-push` 没有位于默认 Skill 根目录，而是某个开发目录，可以加 `--root`：

```powershell
node --experimental-strip-types skills/skill-cleaner/scripts/skill-cleaner.ts --root "D:\XU\Documents\eink-push" --no-logs
```

注意：`--root` 应该指向包含 Skill 目录的根，而不是随便指向一个仓库集合。若输出没有识别到 `eink-push`，把 `--root` 调整到实际安装 Skill 的父目录。

---

## 3. 如何读 skill-cleaner 报告

按上游建议，报告优先看这几个部分：

### 3.1 Skill Budget

这里看 Skill 描述整体占用了多少上下文预算。`skill-cleaner` 按 Codex 类似规则估算：

- 默认读取 `~/.codex/models_cache.json` 的 GPT-5.5 `context_window`。
- 如果读不到，回退到 272,000 tokens。
- 默认按 2% 上下文窗口作为 Skills 预算。
- token 成本近似为 `ceil(utf8_bytes / 4)`。

对 `eink-push` 的意义：

- `description` 必须足够强触发，但不能把完整使用手册塞进描述。
- 真正的流程细节应该放正文，触发词和能力边界放 frontmatter 描述。

### 3.2 Description candidates

这里列出描述过长、可压缩的 Skill。

对 `eink-push` 的检查标准：

- 是否保留核心触发名词：`阅星曈`、`墨水屏`、`推送`、`书架`、`书签`、`联网搜索`。
- 是否避免把所有意图路由都写进 description。
- 是否同时覆盖中文和必要的英文/拼音别名，例如 `Yue Xingtong`、`e-ink`、`epub`。

### 3.3 Duplicates

这里看同名 Skill 或近似 Skill。

对 `eink-push` 的判断：

- 如果出现多个 `eink-push`，保留实际安装目录中的正式版本。
- 如果有旧版、测试版、仓库副本同时被加载，应只让一个版本处于可触发状态。
- 如果 OpenClaw 内置了同类阅星曈推送能力，需要确认哪个版本拥有最新 API 和本地脚本。

### 3.4 Unused candidates

这里看近期没有被触发或读取的 Skill 候选。

不要直接删除。它是启发式判断，只扫描 `$skill`、`Use $skill`、`skills/.../SKILL.md` 等日志痕迹。对 `eink-push` 这种可能由自然语言触发的中文 Skill，未使用判断可能偏保守。

### 3.5 Root summary

这里确认 Skill 来自哪里：

- Codex 系统 Skill。
- 插件缓存 Skill。
- 个人 Skill。
- 项目内或仓库本地 Skill。

对 `eink-push`，最理想的状态是：开发仓库中有一份源代码，实际 OpenClaw/Codex 安装目录中只有一个可触发副本。

---

## 4. skill-cleaner 的清理原则

上游明确强调：先建议，用户要求后再编辑。用于 `eink-push` 时建议遵守：

- 不直接删除未跟踪或被忽略的 Skill 目录，除非确认它是废弃副本。
- 删除重复项前，先确认保留副本存在且会被 Agent 加载。
- 优先删除 repo-local 或 `agent-scripts` 里的重复副本，保留系统内置或正式安装版本。
- `description` 压缩时必须保留触发名词，不要为了省 tokens 把业务关键词删掉。
- 变更分批提交：描述压缩、重复删除、配置禁用分开做，方便回滚。

---

## 5. eink-push 当前形态

当前仓库已经是一个比较完整的 OpenClaw Skill：

- `SKILL.md`：定义触发意图、凭证预检、卡片推送、电子书推送、EPUB 推送、阅读数据拉取、联网搜索和错误处理。
- `scripts/render_image.py`：HTML 卡片截图，转为阅星曈 `.xth` / `.xtg`，多页打包为 `.xtch` / `.xtc`。
- `scripts/render_book.py`：Markdown 经 `marknative` 分页渲染，再打包为 `.xtc` 翻页电子书。
- `scripts/epub/render_book_epub.py`：生成 EPUB，支持 SVG/HTML 封面。
- `scripts/push_to_device.py`：登录阅星曈 API、获取绑定设备、上传 OSS、创建设备任务。
- `scripts/fetch_reading.py`：拉取书架和书签，补充 `clean_name`。
- `scripts/search_query.py`：通过阅星曈服务端搜索接口做实时联网搜索。
- `scripts/check_environment.py`：预检 Python 包、Playwright Chromium、Node.js、npm 和 marknative，并给出修复命令。
- `scripts/check_installation.py`：审计本机常见 Skill 根目录，发现重复安装副本或安装副本与当前源目录漂移。
- `scripts/check_package.py`：审计 git 跟踪 / 未忽略的发布候选内容，防止 `.credentials.json`、`output/`、`node_modules/`、`.venv/`、`.codegraph/` 等敏感或生成内容进入安装包。
- `scripts/install_skill.py`：根据包体审计得到的 runtime 文件集生成安装同步计划；默认 dry-run，只在显式 `--apply` 时复制到本机 Skill 目录。自定义 `--target` 必须指向名为 `eink-push` 的 Skill 目录，且不能在当前源码目录内。
- `references/design-guide.md` 与 `references/framework-samples/`：卡片设计规范和样例。
- `agents/openai.yaml`：安装后在 UI 中展示的名称、短描述和默认调用提示。

一句话定位：`eink-push` 是“AI 内容生产 + 墨水屏排版渲染 + 阅星曈云端推送 + 阅读数据反查”的综合 Skill。

---

## 6. 完美 Skill 的目标画像

把 `eink-push` 做成“完美 Skill”，不只是让脚本能跑，而是做到：

- **触发准确**：用户说“发到墨水屏”“我的书签”“做成 EPUB”都能稳定命中；普通技术问答不会误触发。
- **上下文经济**：frontmatter 描述短而强，正文只保留 Agent 操作必需的信息，长参考放 `references/`。
- **流程可恢复**：凭证缺失、依赖缺失、网络失败、设备未绑定、渲染失败都有明确下一步。
- **产物可靠**：卡片不溢出，长文分页稳定，EPUB 能在设备阅读器里打开。
- **安全可解释**：账号密码优先从环境变量读取，兼容本地 `.credentials.json`，只发往官方域名，日志不泄露凭证。
- **可测试**：离线渲染、格式编码、Markdown 预处理、API 响应解析都有最小回归测试。
- **可维护**：脚本边界清晰，共用逻辑不重复，README 给用户，SKILL 给 Agent，SETUP 给排障。

---

## 7. 优化路线

### P0：先保证安全与可用

1. **修正 `SKILL.md` 意图路由表的小格式问题**（已完成）

   原 EPUB 路由行前面多了一个 `|`，容易影响 Markdown 表格阅读：

   ```markdown
   || 明确说「epub / EPUB / epub格式」 | → **推送：EPUB 电子书** |
   ```

   建议改成：

   ```markdown
   | 明确说「epub / EPUB / epub格式」 | → **推送：EPUB 电子书** |
   ```

2. **把 `.codegraph/` 加入 `.gitignore`**（已完成）

   本项目已经初始化 CodeGraph，`.codegraph/` 是本地索引目录，不应进入 git。建议加入：

   ```gitignore
   .codegraph/
   ```

3. **统一凭证读取逻辑**（已完成第一版）

   `push_to_device.py`、`fetch_reading.py`、`search_query.py` 都有凭证/登录逻辑，其中 `fetch_reading.py` 复用了 `push_to_device.py`，但 `search_query.py` 自己复制了一份。已抽出：

   ```text
   scripts/xteink_api.py
   ```

   放入：

   - `BASE_URL`
   - `HTTP_TIMEOUT`
   - `load_credentials`
   - `login`
   - `auth_headers`
   - `format_http_error`

4. **凭证预检不要只检查文件存在**（已完成结构检查）

   `--check-credentials` 已从只判断文件存在，升级为验证环境变量或 JSON 是否可读、字段是否完整。需要真实登录时可加 `--auth`。当前分层输出：

   - `MISSING`：文件不存在。
   - `INVALID`：环境变量只配置一半、JSON 损坏或缺字段。
   - `OK`：结构完整。
   - `AUTH_OK`：实际登录成功（仅 `--check-credentials --auth`）。
   - `AUTH_FAILED: ...`：实际登录或网络校验失败。

   这样 Agent 能更准确地引导用户，而不是等推送时才失败。

5. **支持 OpenClaw 环境变量注入凭证**（已完成）

   正式安装环境可优先使用：

   ```text
   XTEINK_USERNAME
   XTEINK_PASSWORD
   ```

   兼容别名：

   ```text
   YUEXINGTONG_USERNAME
   YUEXINGTONG_PASSWORD
   ```

   未设置环境变量时继续读取 `.credentials.json`，保持原有本地开发流程可用。若只设置了用户名或密码的一半，`--check-credentials` 返回 `INVALID`，避免静默 fallback 到旧文件。

### P1：让 Skill 更省上下文、更稳触发

1. **压缩 frontmatter description**（已完成）

   描述已压缩为保留核心触发名词、降低普通搜索误触发的版本：

   ```yaml
   description: >
     将内容推送到阅星曈/Yue Xingtong 墨水屏设备；生成卡片、翻页图片集、
     Markdown/EPUB 电子书；查询书架、阅读进度、书签摘录；必要时调用阅星曈联网搜索。
     用户提到发到墨水屏、阅星曈、书签、书架、阅读进度、EPUB 或实时搜索时使用。
   ```

   保留触发名词，减少解释性句子。

2. **把长流程从 `SKILL.md` 下沉到 `references/`**（已完成第一版）

   `SKILL.md` 已保留决策树和命令索引，详细设计规范、展示格式、衍生内容流程已下沉到：

   - `references/SETUP.md`
   - `references/TROUBLESHOOTING.md`
   - `references/design-guide.md`
   - `references/AGENT-WORKFLOWS.md`

   目标是让 Agent 一眼看到“该走哪条流程”，遇到具体步骤再读取展开文档。

   `scripts/verify.py` 已加入 progressive disclosure 门禁：`SKILL.md`
   正文限制在 500 行以内，正文引用的 `scripts/`、`references/`、
   `assets/` 必须真实存在，且正文不能引用 README、维护方案、手动测试清单等 repo-only 文档。

3. **给联网搜索单独降权**（已完成）

   `description` 已从泛化“查一下最新情况”改为“在阅星曈推送场景中调用联网搜索”。运行正文也明确普通泛化搜索优先用通用搜索能力。

   - 用户明确想把搜索结果推到阅星曈。
   - 用户在阅星曈 Skill 场景中要求搜索。
   - 用户明确要求用阅星曈服务端搜索。

   否则普通最新资讯应由通用搜索或专门新闻 Skill 处理。

4. **补齐安装 / UI 元数据**（已完成）

   已按 `skill-creator` 推荐生成：

   ```text
   agents/openai.yaml
   ```

   当前包含 `display_name`、`short_description` 和显式引用 `$eink-push` 的 `default_prompt`。`scripts/verify.py` 已覆盖该文件的存在性、LF 行尾、字段集合、短描述长度和默认提示触发词，避免后续安装元数据漂移。

### P2：提高渲染质量

1. **增加卡片 HTML 自动体检**（已完成）

   在 `render_image.py` 截图前后检查：

   - `document.body.scrollHeight` 是否超出目标高度太多。
   - 关键文本是否被裁切。
   - 是否出现横向滚动。
   - 页面背景是否为纯透明或空白。

   当前已在 `render_image.py` 中输出明确警告，帮助 Agent 重写卡片；并补充了实际截图层面的体检，能发现几乎全白 / 全黑或低对比度的 PNG。

2. **预览图默认可选保留**（已完成）

   卡片推送前生成 `.preview.png` 对开发和排障很有价值。可以在文档中建议：

   - 开发调试使用 `--preview`。
   - 正式 Skill 流程默认不保留，避免 output 堆积。

   `references/AGENT-WORKFLOWS.md` 已明确预览策略：开发调试或排障时可加 `--preview`，正式 Skill 推送命令默认不带 `--preview`。`scripts/verify.py` 已加入门禁，确保 README / SETUP 的本地验证保留 `--preview`，且 SKILL / AGENT-WORKFLOWS 的正式推送命令不把 `--preview` 和 `--push` 混用。

3. **Markdown 预处理增加测试样例**

   `render_book.py` 已经处理 frontmatter 和 GFM 表格转列表，这是很关键的稳定性逻辑。建议为这些函数加最小测试：

   - YAML frontmatter title 变成 `# title`。
   - `style` 字段被跳过。
   - URL 中的冒号不被截断。
   - 表格转成列表。
   - fenced code block 内的 `|` 不被误判为表格。

4. **EPUB 路径增加 smoke test**

   `render_book_epub.py` 功能多、风险也高。建议新增一个不推送的验证命令：

   ```powershell
   python scripts/epub/render_book_epub.py output/test.md --title "测试" --author "龙虾" --cover-svg
   ```

   并在 `references/SETUP.md` 里补充 EPUB 验证。

### P3：提高 API 与错误处理质量

1. **统一 stdout / stderr 契约**（已完成第一版）

   `fetch_reading.py` 和 `search_query.py` 已经把 JSON 放 stdout、进度放 stderr。生成类脚本已统一在成功后输出 `OUTPUT:<path>`，便于 Agent 稳定识别产物路径。

   - 机器可读结果只写 stdout。
   - 进度和错误写 stderr。
   - 成功产物统一输出 `OUTPUT:<path>`。

2. **API 响应字段做兼容层**（已完成第一版）

   `push_to_device.py` 原本兼容 `access_token` / `token`、`data` / `devices`。当前已把这类兼容策略集中到 `scripts/xteink_api.py`：

   - `extract_access_token`
   - `extract_devices`
   - `normalize_device`
   - `select_default_device`

   单测覆盖顶层 / 嵌套 token、列表 / 字典设备响应、设备字段别名、默认设备选择和错误分支。

3. **为读取数据命令增加 `--jsonl` 或 `--compact`**（已完成）

   书架和书签很多时，完整 JSON 会很长。已新增 Agent 友好输出：

   - `--compact`：只返回展示必要字段。
   - `--limit`：限制输出条数。
   - 默认不加 `--compact` 时仍保留完整响应。

   `tests/test_fetch_reading.py` 已覆盖书名清洗、书架 compact、书签 compact、limit 截断元数据和不截断分支。`scripts/verify.py` 已加入文档门禁，确保 `SKILL.md`、`references/AGENT-WORKFLOWS.md`、`references/MANUAL-TEST-CHECKLIST.md` 持续建议默认 `--compact --limit`，并说明何时去掉这些参数。

### P4：完善用户体验

1. **README 增加“开发者快速验证”**

   README 面向使用者很好，但开发者第一次 clone 后还需要知道：

   - Python 依赖。
   - Node 依赖。
   - 如何离线测试卡片。
   - 如何离线测试电子书。
   - 哪些命令会真实推送设备。

2. **增加常见用户话术到 `SKILL.md`**（已完成）

   `SKILL.md` 已在正文的意图路由前保留少量高价值触发句：

   - “把这段发到阅星曈”
   - “做成墨水屏卡片”
   - “生成 EPUB 发到设备”
   - “看一下我的书架”
   - “整理《书名》的书签”

   这些示例未放入 frontmatter，避免增加全局 description 成本。`scripts/verify.py` 已加入门禁：要求这些话术出现在正文中，同时禁止它们泄漏到 frontmatter description。

3. **把 ONBOARDING-COPY 变成安装后清单**（已完成）

   `references/ONBOARDING-COPY.md` 已作为首次配置 / 首次推送成功后的引导清单保留，并由 `SKILL.md` 在首次写入或覆盖 `.credentials.json` 后显式读取。它包含：

   - 已保存凭证。
   - 如何测试一次推送。
   - 如何查询书架。
   - 如何重置凭证。
   - 隐私说明。

   已修正默认格式说明：长文默认是 Markdown 翻页电子书，只有用户明确说 `EPUB` / `epub 格式` 时才生成 EPUB。`scripts/verify.py` 已加入 onboarding 文档一致性检查，覆盖主流程引用、凭证检查命令和 stale EPUB 默认文案。

---

## 8. 建议的实施顺序

### 第一轮：低风险清理

- [x] 修正 `SKILL.md` EPUB 表格行。
- [x] `.gitignore` 增加 `.codegraph/`。
- [x] README 补充开发验证入口。
- [x] `references/SETUP.md` 增加 EPUB smoke test。

### 第二轮：结构优化

- [x] 新增 `scripts/xteink_api.py`，统一凭证、登录、headers。
- [x] 改造 `push_to_device.py`、`fetch_reading.py`、`search_query.py` 使用共享 API helper。
- [x] 改进 `--check-credentials` 输出结构。
- [x] 支持 `XTEINK_USERNAME` / `XTEINK_PASSWORD` 环境变量优先读取凭证，并兼容 `.credentials.json`。
- [x] 增加 `--check-credentials --auth` 实际登录校验。
- [x] 继续统一 HTTP 错误格式化。

### 第三轮：质量保障

- [x] 新增测试目录，例如 `tests/`。
- [x] 覆盖 Markdown 预处理、书名清洗、格式映射、凭证状态、headers。
- [x] 覆盖容器编码头部。
- [x] 覆盖卡片布局体检判断逻辑。
- [x] 覆盖卡片实际截图空白 / 低对比体检判断逻辑。
- [x] 加一个不联网 smoke test：HTML → preview PNG，Markdown → XTC；缺依赖时明确 SKIP。
- [x] 加入 `scripts/verify.py` 聚合语法检查、单测、凭证结构检查、离线 smoke test。
- [x] 将 `SKILL.md` frontmatter 校验加入 `scripts/verify.py`，覆盖 BOM、CRLF、非法顶层字段和描述长度。
- [x] 将 `SKILL.md` 正文 progressive disclosure 校验加入 `scripts/verify.py`，覆盖正文行数、必需引用、资源存在性、repo-only 引用和深层 reference。
- [x] 新增 `agents/openai.yaml`，补齐 Skill UI 名称、短描述和默认提示。
- [x] 将 `agents/openai.yaml` 校验加入 `scripts/verify.py`。
- [x] 将首次配置后的 `ONBOARDING-COPY.md` 引导接回 `SKILL.md` 主流程。
- [x] 将 onboarding / README 凭证检查与 EPUB 默认格式一致性加入 `scripts/verify.py`。
- [x] 新增 `scripts/check_environment.py`，统一安装依赖预检与修复命令输出。
- [x] 将环境预检接入 `SKILL.md`、`README.md`、`references/SETUP.md`、`references/TROUBLESHOOTING.md` 和 `scripts/verify.py`。
- [x] 新增 `scripts/check_installation.py`，检查本机 Skill 安装根目录中的重复副本和源/安装漂移。
- [x] 将安装审计接入 `README.md`、`references/SETUP.md` 和 `scripts/verify.py`。
- [x] 新增 `scripts/check_package.py`，检查 git 跟踪 / 未忽略内容是否混入 `.credentials.json`、`output/`、`node_modules/`、`.venv/`、`.codegraph/` 或其他未分类发布文件。
- [x] 将发布包内容审计接入 `README.md`、`references/SETUP.md` 和 `scripts/verify.py`。
- [x] 新增 `scripts/install_skill.py`，默认 dry-run 预览安装同步计划，显式 `--apply` 时复制 runtime 文件到本机 Skill 目录。
- [x] 统一 `render_image.py`、`render_book.py`、`render_book_epub.py` 成功输出 `OUTPUT:<path>`，并在 smoke test 中校验。
- [x] 将登录 token 与绑定设备响应兼容层集中到 `scripts/xteink_api.py`，并补充单测。
- [x] 将读取数据 `--compact/--limit` 文档契约加入 `scripts/verify.py`。
- [x] 将 5 条高价值用户话术加入 `SKILL.md` 正文，并用 `scripts/verify.py` 防止误塞进 description。
- [x] 明确卡片预览策略：开发调试用 `--preview`，正式推送命令默认不保留预览图，并加入 `scripts/verify.py`。
- [x] 增加 `.gitattributes` 固定 Skill 与脚本文本为 LF，避免 Windows checkout 破坏 frontmatter 校验。
- [x] 加入 `requirements.txt`，统一声明 Python 运行依赖。
- 把真实推送测试标记为手动测试，避免 CI 需要凭证和设备。
- [x] 增加真实推送手动测试清单 `references/MANUAL-TEST-CHECKLIST.md`。

2026-05-26 验证结果：

- 使用仓库内 `.venv` 安装 `requirements.txt` 后，`scripts/verify.py` 通过。
- 单元测试：92 tests OK。
- Skill 元数据校验：`SKILL.md` 通过，且 `scripts/verify.py` 已覆盖该检查。
- Skill description 预算校验：frontmatter description 限制在 220 字 / 约 90 tokens 内，必须保留核心触发词，并禁止把“最新资讯”“搜一下”等泛化搜索触发词塞进 description。
- Skill 正文校验：`SKILL.md` 正文 267 行，低于 500 行门槛；正文资源引用均存在，未引用 README、维护方案、手动测试清单等 repo-only 文档。
- UI 元数据校验：`agents/openai.yaml` 通过，且 `scripts/verify.py` 已覆盖该检查。
- Onboarding 文档校验：`SKILL.md`、`README.md`、`references/ONBOARDING-COPY.md` 通过一致性检查。
- 凭证来源校验：`SKILL.md`、`README.md`、`references/SETUP.md`、`references/TROUBLESHOOTING.md` 均说明环境变量优先、`.credentials.json` fallback。
- 读取数据文档校验：`SKILL.md`、`references/AGENT-WORKFLOWS.md`、`references/MANUAL-TEST-CHECKLIST.md` 持续要求默认 `--compact --limit`。
- 触发话术校验：5 条高价值用户话术位于 `SKILL.md` 正文，未进入 frontmatter description。
- 预览策略校验：README / SETUP 用 `--preview` 做本地验证，正式推送命令不混用 `--preview --push`。
- 环境预检：`python scripts/check_environment.py` 输出全 OK；Python 3.11.9、Playwright Chromium、Node.js v22.19.0、npm、marknative 均可用。
- 安装副本审计：`python scripts/check_installation.py --require-installed` 已发现 `C:\Users\zihen\.codex\skills\eink-push` 安装副本和 `D:\XU\Documents\eink-push` 源目录，`SKILL.md` / `agents/openai.yaml` 未漂移，未发现重复安装副本。
- 发布包内容审计：`python scripts/check_package.py` 检查 git 跟踪 / 未忽略文件，当前 81 个候选文件中 57 个为 runtime、24 个为 repo-only；安装审计、包体审计、总验证和手动测试清单等维护内容不会进入安装同步计划。
- 安装同步预览：`python scripts/install_skill.py` 默认只输出安装计划，不写文件；`--apply` 才同步 57 个 runtime 文件到本机 Skill 目录；目标路径会校验目录名和源码树包含关系，避免误写当前仓库。已验证源码树内目标会被拒绝。安装副本运行后生成的 `node_modules/`、`output/` 和 `__pycache__/` 属于目标端受保护运行产物，不会被 dry-run 误报为 extra。
- 安装副本 runtime 验证：在 `C:\Users\zihen\.codex\skills\eink-push` 内运行 `npm install marknative` 后，`python scripts/check_environment.py` 全 OK；`render_image.py`、`render_book.py`、`render_book_epub.py` 均能从安装副本离线生成产物。正式安装副本不包含 `check_package.py`、`install_skill.py`、`smoke_test.py`、`verify.py` 等 repo-only 维护脚本。
- 卡片截图体检：空白图、低对比图、正常高对比图均有单测覆盖。
- 生成产物输出契约：HTML 卡片、Markdown 翻页电子书、EPUB smoke test 均校验 `OUTPUT:<path>`。
- API 响应兼容层：登录 token、设备列表、设备归一化、默认设备选择均有单测覆盖。
- Markdown → XTC smoke：通过。
- Markdown → EPUB smoke：通过。
- HTML → XTH smoke：非沙箱运行 `scripts/verify.py` 通过，已生成 `output/smoke/smoke-card.xth` 和 `output/smoke/smoke-card.preview.png`。Codex 沙箱内若出现 `spawn EPERM` 会被明确标记为 SKIP。
- 实际登录校验：`python scripts/push_to_device.py --check-credentials --auth` 输出 `OK` + `AUTH_OK`。
- 真实设备推送烟测：
  - `output/smoke/smoke-card.xth` 推送成功，设备路径 `/Pushed Images/smoke-card.xth`，任务 ID `0ea2709f05dc44a4a71654d4b7afae82`。
  - `output/smoke/smoke-book.xtc` 推送成功，设备路径 `/Pushed Images/smoke-book.xtc`，任务 ID `7471c63c921c4331bee9838ba93a70bf`。
  - `output/smoke/smoke-book.epub` 推送成功，设备路径 `/Pushed Books/smoke-book.epub`，任务 ID `b5ab0bf0-2d28-4f16-9653-11bdf7cde990`。

### 第四轮：Skill 预算审计

- [x] 用 `skill-cleaner --no-logs` 看 description 成本和重复项。
- [x] 用 `skill-cleaner --months 6 --deep-logs` 看真实触发情况。
- [x] 根据报告压缩 description 或禁用重复副本。
- [x] 将 description 预算与泛化搜索触发短语加入 `scripts/verify.py` 门禁。

2026-05-26 轻量审计结果：

- 以 `D:\XU\Documents\eink-push` 为 root：发现 11 个 skills，考虑 10 个，预算使用 1,225 / 5,440 tokens（22.5%）。
- `eink-push` description 为 136 字符，rendered line 为 193 字符，无同名重复，无删除建议。
- 报告显示无需禁用重复副本；当前用 `scripts/verify.py` 持续约束 description 不回涨、不误吸收通用搜索触发词。
- `skill-refs/` 中的参考 Skill 会被本地扫描发现；该目录已加入 `.gitignore`，避免进入正式安装包。若本地继续放参考仓库，运行审计时需忽略这些 extra 项。
- `--no-logs` 下 unused 判断没有日志依据，`eink-push` 被列入 unused 不能作为删除依据。
- `--deep-logs --months 6` 扫描 93 个日志文件后仍未发现本开发目录下 `eink-push` 的使用痕迹；这说明当前仓库副本主要是开发源，不代表正式安装目录未被使用。

---

## 9. 完成标准

`eink-push` 可以认为达到高质量 Skill 状态时，应满足：

- `skill-cleaner` 不报告同名高风险重复项。
- `description` 保留核心触发词，且不属于明显过长候选。
- 凭证缺失、凭证损坏、账号错误分别有清晰输出。
- 卡片、Markdown 电子书、EPUB 都有离线 smoke test。
- 安装依赖可用 `scripts/check_environment.py` 一键预检，并能输出具体修复命令。
- `scripts/verify.py` 可一键运行离线验证。
- API helper 复用后没有三份登录代码。
- `SKILL.md` 只承载路由和关键命令，长解释在 `references/`。
- `agents/openai.yaml` 存在且默认提示明确引用 `$eink-push`。
- README 面向用户，SETUP 面向安装排障，优化/维护文档面向开发者。

---

## 10. 一句话结论

`skill-cleaner` 应该作为 `eink-push` 的“Skill 层体检工具”：先用它确认触发描述、重复加载和上下文预算；再从 `eink-push` 自身代码出发，补齐凭证、测试、渲染体检、API helper 和文档分层。这样这个 Skill 会从“能用”升级成“稳定、可维护、低误触发、低上下文成本”的成熟 Skill。
