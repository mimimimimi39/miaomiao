@echo off
chcp 936 >nul
title 停止 mimi

echo 正在停止 Cortico...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $_.CommandLine -like '*Cortico*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo Cortico 已停止。

echo.
echo 正在停止空间桥接...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*qzone_web.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo 空间桥接已停止。

echo QQ 协议端（NapCat）请手动关闭那个“管理员: powershell.exe”窗口，
echo 或者直接关闭小号 QQ。
echo.
pause
