@echo off
chcp 936 >nul
title ֹͣ miaomiao

echo ֹͣ Cortico...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $_.CommandLine -like '*Cortico*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo Cortico ֹͣ

echo.
echo ֹͣռŽ...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*qzone_web.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo ռŽֹͣ

echo QQ ЭˣNapCatֶرǸԱ: powershell.exeڣ
echo ֱӹرС QQ
echo.
pause
