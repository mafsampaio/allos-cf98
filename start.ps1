# ============================================================
# WhatsApp Claude Agent — Windows starter
# ============================================================
# Starts webhook_server.py and ngrok tunnel in background.
# Prints the public URL to paste into megaAPI webhook config.
# ============================================================

$ErrorActionPreference = "Stop"

if (-Not (Test-Path "config.py")) {
    Write-Host "ERROR: config.py not found. Run install.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== WhatsApp Claude Agent - Start ===" -ForegroundColor Cyan
Write-Host ""

# --- Kill old processes ---
Write-Host "[1/3] Cleaning old processes..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*webhook*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process ngrok  -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

# --- Start webhook server (background) ---
Write-Host "[2/3] Starting webhook server on :3020..."
Start-Process -FilePath "python" -ArgumentList "webhook_server.py" -WindowStyle Hidden -RedirectStandardOutput "webhook.log" -RedirectStandardError "webhook.err.log"
Start-Sleep -Seconds 2

# --- Start ngrok (background) ---
Write-Host "[3/3] Starting ngrok tunnel..."
Start-Process -FilePath "ngrok" -ArgumentList "http", "3020" -WindowStyle Hidden
Start-Sleep -Seconds 3

# --- Fetch ngrok URL via local API ---
try {
    $tunnels = Invoke-RestMethod -Uri "http://127.0.0.1:4040/api/tunnels"
    $publicUrl = $tunnels.tunnels[0].public_url
    Write-Host ""
    Write-Host "=== READY ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Webhook URL (paste into megaAPI):" -ForegroundColor Cyan
    Write-Host "  $publicUrl/?session=1" -ForegroundColor White
    Write-Host ""
    Write-Host "For session 2, 3, ...: append ?session=N"
    Write-Host ""
    Write-Host "Next: in Claude Code session, set Monitor to:"
    Write-Host "  python monitor.py 1" -ForegroundColor White
    Write-Host ""
    Write-Host "Logs: webhook.log / webhook.err.log"
    Write-Host "Stop: .\stop.ps1"
} catch {
    Write-Host "WARNING: Could not fetch ngrok URL. Check: http://127.0.0.1:4040" -ForegroundColor Yellow
}
