@echo off
setlocal
cd /d "%~dp0.."
echo Restarting mimi...
call stop_cortico.bat /quiet
ping 127.0.0.1 -n 3 >nul
call start_cortico.bat /quiet
echo Restart finished.
pause
