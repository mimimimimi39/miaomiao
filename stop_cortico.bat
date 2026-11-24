@echo off
setlocal
echo Stopping mimi...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'bin/cortico\.mjs mybot|NapCat\\index\.js|napcat\.mjs|qzone_web\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo Done.
if /I not "%~1"=="/quiet" pause
