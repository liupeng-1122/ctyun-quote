# 天翼云等保报价系统 - Android 使用指南

## 方式一：PWA 安装到手机桌面（推荐，立即可用）

这是最快的方式，不需要任何工具，直接通过手机浏览器即可使用。

### 步骤

1. **确保电脑和手机在同一 WiFi 网络下**
2. **在电脑上启动 Flask 服务**
   ```
   cd 项目目录
   py app.py
   ```
   看到输出 `http://0.0.0.0:5000` 即表示启动成功。
3. **查看电脑的局域网 IP**
   - Windows: 打开命令提示符，输入 `ipconfig`
   - 找到 `IPv4 地址`，例如 `192.168.1.100`
4. **在手机浏览器中访问**
   - 打开 Chrome 浏览器
   - 输入 `http://192.168.1.100:5000`（将 IP 替换为你的实际 IP）
5. **添加到手机桌面（PWA 安装）**
   - Chrome 菜单 → 「添加到主屏幕」
   - 或者底部弹出的提示中点击「安装」
   - 之后就可以像原生 App 一样从桌面打开使用

> ⚠️ 每次使用前需要在电脑上先运行 `py app.py`

---

## 方式二：GitHub Actions 构建 APK（免费云编译）

推荐方案，完全免费，无需任何本地工具，构建完成后可以得到一个真正的 `.apk` 安装包。

### 前置条件

- 一个 GitHub 账号
- Git 已安装

### 步骤

1. **在 GitHub 上创建仓库**
   - 登录 GitHub，点击右上角 `+` → `New repository`
   - 输入仓库名（如 `ctyun-quote`）
   - 选择 `Private` 或 `Public`
   - 点击 `Create repository`

2. **推送代码到 GitHub**
   ```bash
   cd 项目目录
   git init
   git add .
   git commit -m "首次提交：天翼云等保报价系统"
   git remote add origin https://github.com/你的用户名/ctyun-quote.git
   git push -u origin main
   ```

3. **触发构建**
   - 打开 GitHub 仓库页面
   - 点击 `Actions` 标签
   - 在左侧选择 `构建 Android APK`
   - 点击右侧 `Run workflow` → `Run workflow`
   - 等待约 1-2 小时（首次需要下载 Android SDK）

4. **下载 APK**
   - 构建完成后，在 Actions 页面点击该次运行的 `Summary`
   - 在 `Artifacts` 区域下载 `CtyunQuote-APK.zip`
   - 解压后得到 `.apk` 文件
   - 将 `.apk` 传到手机安装即可

---

## 方式三：Docker 本地构建 APK

如果电脑上 Docker Desktop 运行正常，可以使用以下命令：

### PowerShell（管理员模式）
```powershell
.\docker_build_apk.ps1
```

### 或手动执行
```bash
docker run --rm -v ${PWD}:/workspace -w /workspace kivy/buildozer:latest buildozer android debug
```

构建完成后在 `bin/` 目录下获取 `.apk` 文件。

---

## 直接网页版使用（无需安装）

如果只是想快速使用报价功能，电脑上直接访问：
```
http://localhost:5000
```

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `app.py` | Flask 网页服务端 |
| `templates/index.html` | 手机版前端页面 |
| `static/style.css` | 样式文件 |
| `static/app.js` | 前端交互逻辑 |
| `android_main.py` | Android 应用入口脚本 |
| `buildozer.spec` | Buildozer 构建配置 |
| `.github/workflows/build_apk.yml` | GitHub Actions 自动构建 |
| `docker_build_apk.ps1` | Docker 构建脚本 |
| `scripts/` | 业务逻辑（不变） |