@echo off
chcp 936 >nul
title mimi һ
setlocal

set "ROOT=<AiQQ>"
set "CORTICO=%ROOT%\Cortico"
set "NODEDIR=C:\AAA\node\node-v22.23.5-win-x64"
set "PATH=%NODEDIR%;%PATH%"

echo ========================================
echo   mimi һֻ Cortico
echo ========================================
echo.

echo [1/4] ֹͣ Cortico...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { $_.CommandLine -like '*cortico*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 3 >nul

echo [2/4]  Cortico...
start "" cmd /c "cd /d %CORTICO% && node bin/cortico.mjs mybot > %CORTICO%\cortico_out.txt 2>&1"

echo [3/4] ȴ WebUI...
set /a n=0
:wait
timeout /t 3 >nul
set /a n+=1
netstat -ano | findstr ":7788 " | findstr LISTENING >nul
if %errorlevel%==0 goto :ready
if %n% geq 20 goto :fail
goto :wait

:ready
echo [4/4] ָ¼...
curl -s --noproxy "*" -X POST http://127.0.0.1:7788/api/run/resume -H "Content-Type: application/json" -d "{}"
echo.
echo ----------------------------------------
echo ɣmimi ָ
echo WebUI: http://127.0.0.1:7788/
echo ----------------------------------------
pause
exit /b 0

:fail
echo.
echo [ʧ] WebUI û鿴־
echo   %CORTICO%\cortico_out.txt
pause
exit /b 1
