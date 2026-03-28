# 推送故障排查

推送失败时，根据错误类型给出以下提示：

| 错误 | 用户提示 |
|------|---------|
| 网络超时 | `推送超时，请检查网络连接后重试：python scripts/push_to_device.py <文件>` |
| 账号密码错误（401） | 告知用户"账号或密码有误"，删除 `eink-push/.credentials.json`，重新执行凭证预检步骤向用户收集正确账号。 |
| 未找到绑定设备 | `未找到绑定设备，请先在阅星曈 App 中绑定设备。` |
| 其他错误 | 将脚本原始报错贴给用户，说明需要手动排查。 |

## 重置凭证

让用户说"重置阅星曈账号"，删除 `eink-push/.credentials.json` 后重新收集账号密码。

```bash
# 删除凭证文件（Windows PowerShell）
Remove-Item eink-push/.credentials.json
```
