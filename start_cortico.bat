@echo off
setlocal
cd /d "%~dp0"

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "NAPCAT=%ROOT%\NapCat"
set "CORTICO=%ROOT%\Cortico"

where node >nul 2>&1
if errorlevel 1 goto :no_node

netstat -ano | findstr ":3000 " | findstr LISTENING >nul
if not errorlevel 1 goto :napcat_ready

if not exist "%NAPCAT%\napcat.bat" goto :no_napcat

echo [1/3] Starting NapCat...
start "" /min "%ROOT%\tools\start_napcat.cmd"
set /a n=0
:wait_napcat
ping 127.0.0.1 -n 4 >nul
netstat -ano | findstr ":3000 " | findstr LISTENING >nul
if not errorlevel 1 goto :napcat_ready
set /a n+=1
if %n% lss 40 goto :wait_napcat
echo [error] NapCat did not open port 3000.
echo         Check: %CORTICO%\napcat_out.txt
if /I not "%~1"=="/quiet" pause
exit /b 1

:napcat_ready
echo [1/3] NapCat is listening on 3000.

netstat -ano | findstr ":7788 " | findstr LISTENING >nul
if not errorlevel 1 goto :cortico_ready
if not exist "%CORTICO%\bin\cortico.mjs" goto :no_cortico

echo [2/3] Starting Cortico...
start "" /min "%ROOT%\tools\start_cortico_node.cmd"
set /a n=0
:wait_cortico
ping 127.0.0.1 -n 4 >nul
netstat -ano | findstr ":7788 " | findstr LISTENING >nul
if not errorlevel 1 goto :cortico_ready
set /a n+=1
if %n% lss 40 goto :wait_cortico
echo [error] Cortico did not open port 7788.
echo         Check: %CORTICO%\cortico_out.txt
if /I not "%~1"=="/quiet" pause
exit /b 1

:cortico_ready
echo [2/3] Cortico is listening on 7788.

netstat -ano | findstr ":8090 " | findstr LISTENING >nul
if not errorlevel 1 goto :resume
where pythonw >nul 2>&1
if errorlevel 1 goto :no_pythonw
echo [2.5/3] Starting optional QZone bridge...
start "" pythonw "%ROOT%\tools\qzone_web.py"
goto :resume

:no_pythonw
echo [2.5/3] pythonw not found; QZone bridge skipped.

:resume
echo [3/3] Resuming Cortico run loop...
curl.exe -s --noproxy "*" -X POST http://127.0.0.1:7788/api/run/resume -H "Content-Type: application/json" -d "{}"
echo.
echo mimi is starting.
echo   Cortico WebUI: http://127.0.0.1:7788/
echo   NapCat WebUI:  http://127.0.0.1:6099/
echo   Logs:          %CORTICO%\cortico_out.txt
if /I not "%~1"=="/quiet" pause
exit /b 0

:no_node
echo [error] Node.js 22+ was not found in PATH.
echo         Install Node.js and reopen this window.
if /I not "%~1"=="/quiet" pause
exit /b 1

:no_napcat
echo [error] NapCat not found: %NAPCAT%\napcat.bat
if /I not "%~1"=="/quiet" pause
exit /b 1

:no_cortico
echo [error] Cortico not found: %CORTICO%\bin\cortico.mjs
if /I not "%~1"=="/quiet" pause
exit /b 1
