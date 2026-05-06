# 天翼云等保报价系统 - Docker APK 构建脚本
# 使用方法: 以管理员身份运行 PowerShell，然后执行 .\docker_build_apk.ps1

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  天翼云等保报价系统 - APK 构建脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Docker 是否运行
try {
    $dockerInfo = docker stats --no-stream 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Docker 未运行"
    }
    Write-Host "[✓] Docker 已就绪" -ForegroundColor Green
} catch {
    Write-Host "[!] Docker 未运行，尝试启动..." -ForegroundColor Yellow
    try {
        Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe" -WindowStyle Hidden
        Write-Host "[!] 正在等待 Docker 启动（约60秒）..." -ForegroundColor Yellow
        Start-Sleep -Seconds 60
    } catch {
        Write-Host "[✗] 无法启动 Docker Desktop" -ForegroundColor Red
        Write-Host ""
        Write-Host "请手动启动 Docker Desktop 后重试，或者使用 GitHub Actions 构建（详见 README）" -ForegroundColor Yellow
        exit 1
    }
}

# 创建图标（如不存在）
if (-not (Test-Path "icons\icon.png")) {
    Write-Host "[.] 创建应用图标..." -ForegroundColor Yellow
    $null = New-Item -ItemType Directory -Force -Path "icons"
    py -c "
import struct, zlib
def create_png(path, w, h, r, g, b):
    raw = b''
    for y in range(h):
        raw += b'\x00'
        for x in range(w):
            raw += bytes([r, g, b, 255])
    compressed = zlib.compress(raw)
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', ihdr)
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(png)
create_png('icons/icon.png', 192, 192, 44, 95, 138)
print('图标已创建')
"
    Write-Host "[✓] 图标已创建" -ForegroundColor Green
}

# 拉取 Buildozer Docker 镜像
Write-Host "[.] 拉取 Buildozer Docker 镜像..." -ForegroundColor Yellow
docker pull kivy/buildozer:latest
if ($LASTEXITCODE -ne 0) {
    Write-Host "[✗] 拉取镜像失败" -ForegroundColor Red
    exit 1
}
Write-Host "[✓] 镜像已就绪" -ForegroundColor Green

# 构建 APK
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  开始构建 APK（首次约 30-60 分钟）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

docker run --rm `
    -v ${PWD}:/workspace `
    -w /workspace `
    kivy/buildozer:latest `
    buildozer android debug

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  [✓] APK 构建成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Get-ChildItem -Path "bin\*.apk" | ForEach-Object {
        Write-Host "  > $($_.FullName) ($([math]::Round($_.Length / 1MB, 1)) MB)" -ForegroundColor Cyan
    }
} else {
    Write-Host ""
    Write-Host "[✗] APK 构建失败，请检查日志" -ForegroundColor Red
}