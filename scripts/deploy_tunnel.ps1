# SDAI - Deploy automatizado con Cloudflare Tunnel
#
# Automatiza:
#   1. Verifica .env existe
#   2. Descarga cloudflared.exe si falta
#   3. Arranca backend uvicorn en background
#   4. Espera healthcheck
#   5. Levanta tunnel Cloudflare quick URL
#   6. Imprime URL publica para compartir
#
# Uso:
#   .\scripts\deploy_tunnel.ps1
#
# Detener todo:
#   .\scripts\deploy_tunnel.ps1 -Stop

param(
    [switch]$Stop,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$CloudflaredPath = Join-Path $ProjectRoot "tools\cloudflared.exe"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# --- Modo Stop ---
if ($Stop) {
    Write-Host "Deteniendo SDAI + tunnel..." -ForegroundColor Yellow

    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) {
        $conn | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            Write-Host "  Backend PID $_ detenido" -ForegroundColor Gray
        }
    }

    Get-Process cloudflared -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force
        Write-Host "  cloudflared PID $($_.Id) detenido" -ForegroundColor Gray
    }

    Write-Host "Todo detenido." -ForegroundColor Green
    exit 0
}

# --- Pre-checks ---
Write-Host "SDAI Deploy Tunnel" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
Write-Host ""

# .env existe?
if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
    Write-Host "ERROR: .env no encontrado en $ProjectRoot" -ForegroundColor Red
    Write-Host "Crealo copiando .env.example y rellenando credenciales." -ForegroundColor Yellow
    exit 1
}
Write-Host "[1/5] .env encontrado" -ForegroundColor Green

# venv Python existe?
if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: venv no encontrado en $VenvPython" -ForegroundColor Red
    Write-Host "Crea con: python -m venv .venv && .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}
Write-Host "[2/5] venv listo" -ForegroundColor Green

# cloudflared.exe existe? Si no, descargar
if (-not (Test-Path $CloudflaredPath)) {
    Write-Host "[3/5] cloudflared.exe no encontrado - descargando..." -ForegroundColor Yellow
    $toolsDir = Join-Path $ProjectRoot "tools"
    if (-not (Test-Path $toolsDir)) { New-Item -ItemType Directory -Path $toolsDir | Out-Null }
    $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try {
        Invoke-WebRequest -Uri $url -OutFile $CloudflaredPath -UseBasicParsing
        Write-Host "[3/5] cloudflared descargado" -ForegroundColor Green
    } catch {
        Write-Host "ERROR descargando cloudflared: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[3/5] cloudflared ya instalado" -ForegroundColor Green
}

# Puerto libre?
$existing = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "ADVERTENCIA: puerto $Port ocupado. Liberando..." -ForegroundColor Yellow
    $existing | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
}

# --- Arrancar backend ---
Write-Host "[4/5] Arrancando backend uvicorn..." -ForegroundColor Cyan
$backendLog = Join-Path $ProjectRoot "tools\backend.log"
$backendProc = Start-Process -FilePath $VenvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "$Port", "--log-level", "info" `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError "$backendLog.err" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -PassThru

# Esperar healthcheck
$attempts = 0
while ($attempts -lt 30) {
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/health" -TimeoutSec 2 -ErrorAction Stop
        if ($resp.status -eq "ok") { break }
    } catch {}
    Start-Sleep -Seconds 1
    $attempts++
}
if ($attempts -ge 30) {
    Write-Host "ERROR: backend no respondio en 30s. Ver log: $backendLog" -ForegroundColor Red
    Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    exit 1
}
Write-Host "      Backend OK (PID $($backendProc.Id))" -ForegroundColor Green

# --- Arrancar tunnel ---
Write-Host "[5/5] Levantando Cloudflare Tunnel..." -ForegroundColor Cyan
$tunnelLog = Join-Path $ProjectRoot "tools\tunnel.log"
$tunnelProc = Start-Process -FilePath $CloudflaredPath `
    -ArgumentList "tunnel", "--url", "http://localhost:$Port", "--no-autoupdate" `
    -RedirectStandardOutput $tunnelLog `
    -RedirectStandardError "$tunnelLog.err" `
    -WorkingDirectory $ProjectRoot `
    -WindowStyle Hidden `
    -PassThru

# Esperar URL del tunnel
$tunnelUrl = $null
$attempts = 0
while ($attempts -lt 30 -and -not $tunnelUrl) {
    Start-Sleep -Seconds 1
    if (Test-Path "$tunnelLog.err") {
        $content = Get-Content "$tunnelLog.err" -Raw -ErrorAction SilentlyContinue
        if ($content -match "(https://[a-z0-9-]+\.trycloudflare\.com)") {
            $tunnelUrl = $matches[1]
        }
    }
    $attempts++
}

if (-not $tunnelUrl) {
    Write-Host "ERROR: tunnel no genero URL en 30s. Ver log: $tunnelLog.err" -ForegroundColor Red
    exit 1
}

# --- Resumen ---
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  SDAI EN PRODUCCION" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  URL publica (comparte con quien debas):" -ForegroundColor Cyan
Write-Host "    $tunnelUrl" -ForegroundColor White
Write-Host ""
Write-Host "  Dashboard:" -ForegroundColor Cyan
Write-Host "    $tunnelUrl/dashboard" -ForegroundColor White
Write-Host ""
Write-Host "  Swagger API:" -ForegroundColor Cyan
Write-Host "    $tunnelUrl/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Procesos activos:" -ForegroundColor Cyan
Write-Host "    backend PID $($backendProc.Id)" -ForegroundColor Gray
Write-Host "    tunnel  PID $($tunnelProc.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Logs:" -ForegroundColor Cyan
Write-Host "    Get-Content $backendLog -Wait" -ForegroundColor Gray
Write-Host "    Get-Content $tunnelLog.err -Wait" -ForegroundColor Gray
Write-Host ""
Write-Host "  Para detener todo:" -ForegroundColor Yellow
Write-Host "    .\scripts\deploy_tunnel.ps1 -Stop" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  NO CIERRES esta ventana ni suspendas la laptop." -ForegroundColor Yellow
Write-Host "  El tunnel muere si los procesos terminan." -ForegroundColor Yellow
Write-Host ""

# Copiar URL al clipboard
$tunnelUrl | Set-Clipboard
Write-Host "  URL copiada al portapapeles." -ForegroundColor Green
