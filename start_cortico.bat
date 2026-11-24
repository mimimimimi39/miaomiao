@echo off
chcp 936 >nul
cd /d "%~dp0"

netstat -ano | findstr ":3000 " | findstr LISTENING >nul
if %errorlevel%==0 goto :napcat_ok

echo [1/3]  NapCatNode 棬 UAC...
start "" cmd /c "cd /d C:\AAA\AiQQ\NapCat && napcat.bat > C:\AAA\AiQQ\Cortico\napcat_out.txt 2>&1"
powershell -NoProfile -Command "if (-not (Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'pythonw.exe' -and $_.CommandLine -like '*napcat_qr_watch*' })) { Start-Process pythonw -ArgumentList '%~dp0tools\napcat_qr_watch.py' -WindowStyle Hidden }" >nul 2>&1
echo      ȴ NapCat ߣ״ɨ룩...
set /a n=0

:waitnapcat
timeout /t 3 >nul
set /a n+=1
netstat -ano | findstr ":3000 " | findstr LISTENING >nul
if %errorlevel%==0 goto :napcat_ok
if %n% geq 40 goto :napcat_fail
goto :waitnapcat

:napcat_fail
echo.
echo [ʧ] NapCat ûߣ飺
echo   1. Ƿɨ¼ά NapCat\napcat\cache\qrcode.png
echo   2. ־C:\AAA\AiQQ\Cortico\napcat_out.txt
pause
exit /b 1

:napcat_ok
netstat -ano | findstr ":7788 " | findstr LISTENING >nul
if %errorlevel%==0 goto :cortico_ok

set HTTP_PROXY=

set HTTPS_PROXY=

set ALL_PROXY=

set NO_PROXY=*

set no_proxy=*

netstat -ano | findstr ":8090 " | findstr LISTENING >nul
if errorlevel 1 (
    echo [1.5/3] ռҳŽ...
    start "" pythonw "%~dp0tools\qzone_web.py"
    timeout /t 3 >nul
)

echo [2/3]  Cortico...
start "" cmd /c "set PATH=C:\AAA\node\node-v22.23.5-win-x64;%PATH% && cd /d C:\AAA\AiQQ\Cortico && node bin/cortico.mjs mybot > C:\AAA\AiQQ\Cortico\cortico_out.txt 2>&1"
echo      ȴ WebUI ...
timeout /t 25 >nul
goto :resume

:cortico_ok
echo      Cortico 

:resume
echo [3/3] ָ¼...
curl -s --noproxy "*" -X POST http://127.0.0.1:7788/api/run/resume -H "Content-Type: application/json" -d "{}"
echo.
echo ɣmiaomiao ߡWebUI: http://127.0.0.1:7788/
pause
