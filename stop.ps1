# Stops webhook server + ngrok
$ErrorActionPreference = "SilentlyContinue"

Write-Host "Stopping webhook + ngrok..."
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*python*" } | ForEach-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine
    if ($cmd -like "*webhook_server.py*") { Stop-Process -Id $_.Id -Force }
}
Get-Process ngrok -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "Stopped."
