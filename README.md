# 🔄 Aternos Auto Renew

自动续期 [Aternos](https://aternos.org) 免费 Minecraft 服务器，防止因不活跃而被停用。

## ✨ 功能

- 🕐 每 6 小时自动访问面板保持活跃
- 🐙 通过 GitHub Actions 免费运行（无需服务器）
- 🔐 账号密码通过 GitHub Secrets 安全存储

## 🚀 设置步骤

### 1. Fork 或 Clone 项目

```bash
git clone https://github.com/hotlu/aternos-renew.git
cd aternos-renew
```

### 2. 设置 GitHub Secrets

在 GitHub 仓库中设置以下 Secrets（Settings → Secrets → Actions）：

| Secret | 说明 |
|--------|------|
| `ATERNOS_USERNAME` | Aternos 用户名 |
| `ATERNOS_PASSWORD` | Aternos 密码 |

### 3. 启用 GitHub Actions

进入仓库的 Actions 页面，点击 "I understand my workflows, go ahead and enable them"。

### 4. 手动测试

点击 "Run workflow" 手动触发一次，确认能正常运行。

## 📋 服务器类型说明

Aternos 支持以下服务器类型：

| 类型 | 自定义 JAR | 说明 |
|------|-----------|------|
| **Custom** | ✅ | **可上传任意 server.jar** |
| Paper | ❌ | 选择版本自动安装 |
| Spigot | ❌ | 选择版本自动安装 |
| Forge | ❌ | 选择版本自动安装 |
| Fabric | ❌ | 选择版本自动安装 |
| Vanilla | ❌ | 选择版本自动安装 |
| BungeeCord | ❌ | 选择版本自动安装 |

### 如何上传自定义 server.jar

1. 登录 Aternos → 进入服务器
2. 左侧菜单 → **Settings**
3. **Software** → 选择 **Custom**
4. 上传你的 `server.jar` 文件

## ⚙️ 自定义检查频率

修改 `.github/workflows/renew.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 */6 * * *'  # 每6小时
  # - cron: '0 */12 * * *'  # 每12小时
  # - cron: '0 0 * * *'     # 每天一次
```

## 📄 License

MIT
