$ErrorActionPreference = "SilentlyContinue"
$c = Get-NetTCPConnection -State Listen -LocalPort 3000
if ($c) {
    Stop-Process -Id $c.OwningProcess -Force
}
Start-Sleep -Seconds 5
$c2 = Get-NetTCPConnection -State Listen -LocalPort 3000
if ($c2) {
    Stop-Process -Id $c2.OwningProcess -Force
    Start-Sleep -Seconds 3
}
Start-Process -FilePath "<AiQQ>\NapCat\launcher.bat" -ArgumentList "-q", "<BOT_QQ>" -WorkingDirectory "<AiQQ>\NapCat"
