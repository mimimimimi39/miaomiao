# NapCat restart helper (Administrator required)
# Cleans stuck NapCat processes and re-injects the QQ protocol client.
$ErrorActionPreference = "Continue"

Write-Host "[1/3] Cleaning old NapCat processes..."
Get-Process NapCatWinBootMain -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host ("  kill NapCatWinBootMain {0}" -f $_.Id)
    Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 2

$qq = "C:\qq\QQ.exe"
$hook = "<AiQQ>\NapCat\NapCatWinBootHook.dll"
$boot = "<AiQQ>\NapCat\NapCatWinBootMain.exe"
if (-not (Test-Path $qq)) { Write-Host "QQ not found: $qq"; Read-Host "Press Enter to exit"; exit 1 }
if (-not (Test-Path $hook)) { Write-Host "Hook not found: $hook"; Read-Host "Press Enter to exit"; exit 1 }

Write-Host "[2/3] Starting NapCat (injecting QQ)..."
Start-Process -FilePath $boot -ArgumentList "`"$qq`"", "`"$hook`"", "-q", "<BOT_QQ>" -WindowStyle Normal

Write-Host "[3/3] Waiting for NapCat (up to 90s)..."
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 3
    $conn = Get-NetTCPConnection -State Listen -LocalPort 3000 -ErrorAction SilentlyContinue
    if ($conn) { $ok = $true; break }
}
if ($ok) {
    Write-Host "NapCat is online (port 3000)"
    try {
        $info = Invoke-RestMethod -Uri "http://127.0.0.1:3000/get_login_info" -TimeoutSec 8
        Write-Host ("Logged in: {0} ({1})" -f $info.data.nickname, $info.data.user_id)
    } catch {
        Write-Host "Not logged in yet. Please scan the QR code."
        $qr = "<AiQQ>\NapCat\cache\qrcode.png"
        if (Test-Path $qr) { Start-Process $qr }
    }
} else {
    Write-Host "NapCat did not come online. Check:"
    Write-Host "  1) UAC prompt accepted"
    Write-Host "  2) QQ version compatible (9.9.37-54395 mapping patched in napcat.mjs)"
    Write-Host "  3) Logs: <AiQQ>\NapCat\logs"
}
Read-Host "Press Enter to close"
