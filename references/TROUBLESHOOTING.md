# 推送故障排查

推送失败时，先保留脚本原始输出，再按下表处理。所有命令默认在 `eink-push/` 根目录执行。

| 错误 / 输出 | 处理 |
|------|------|
| `MISSING` / `[CREDENTIALS_MISSING]` | 询问用户阅星曈手机号和密码；优先配置 `XTEINK_USERNAME` / `XTEINK_PASSWORD`，或写入 `.credentials.json` 后重试。 |
| `INVALID` / `[CREDENTIALS_INVALID]` | 若环境变量只设置了一半，同时补齐 `XTEINK_USERNAME` / `XTEINK_PASSWORD`；否则重新收集手机号和密码并覆盖 `.credentials.json`。 |
| `AUTH_FAILED: ...` | 读取失败原因；401 走重置凭证，网络错误走网络排查。 |
| 账号密码错误 / 401 | 运行 `python scripts/push_to_device.py --reset-credentials` 或更新环境变量，重新收集账号密码。 |
| 未找到绑定设备 | 告知用户先在阅星曈 App 中绑定设备，再重试推送。 |
| 网络超时 | 提醒检查网络后重试；若持续失败，稍后再试或更换网络。 |
| `check_environment.py` 显示 `MISSING` / `FAIL` | 先按对应 `fix:` 命令处理，再重跑 `python scripts/check_environment.py`。 |
| `requests 未安装` | 运行 `pip install requests`。 |
| `Playwright 未安装` | 运行 `pip install playwright`，然后 `playwright install chromium`。 |
| `Pillow 未安装` | 运行 `pip install Pillow`。 |
| `marknative 未安装` | 在 Skill 根目录运行 `npm install marknative`。 |
| `skia-canvas` native 模块报错 | 先 `npm rebuild skia-canvas`；仍失败时使用 Node.js 最新 LTS 后重新 `npm install marknative`。 |
| HTML 卡片出现 `[WARN] 内容高度...` | 内容过多，优先拆成多张卡片；若是长文，改走 Markdown 电子书。 |
| HTML 卡片出现 `[WARN] 页面宽度...` | 检查 CSS 固定宽度、长 URL、表格或代码块，避免横向溢出。 |
| HTML 卡片出现 `[WARN] 截图几乎全白/全黑` | 检查 HTML 是否为空、文字颜色是否和背景相同、主要内容是否被绝对定位元素遮挡。 |
| HTML 卡片出现 `[WARN] 截图灰度变化很小` | 提高文字与背景对比度，避免浅灰字、低透明度文字或过淡背景。 |
| smoke test 显示 `spawn EPERM` | 当前环境禁止启动 Playwright Chromium；在真实本地终端或允许启动浏览器的环境重跑 HTML 卡片验证。 |
| 其他错误 | 将完整报错原文展示给用户，说明需手动排查。 |

## 快速检查

```bash
python scripts/push_to_device.py --check-credentials
python scripts/push_to_device.py --check-credentials --auth
python scripts/check_environment.py
python scripts/smoke_test.py
```

`smoke_test.py` 不会推送设备；缺依赖的路径会显示 `SKIP`。

## 重置凭证

```bash
python scripts/push_to_device.py --reset-credentials
```

重置后重新收集账号密码，写入：

```json
{
  "username": "手机号",
  "password": "密码"
}
```

正式安装环境也可以不写文件，改为设置：

```powershell
$env:XTEINK_USERNAME="手机号"
$env:XTEINK_PASSWORD="密码"
```
