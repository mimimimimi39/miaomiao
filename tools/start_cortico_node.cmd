@echo off
setlocal
set "CORTICO_START_PAUSED=0"
cd /d "%~dp0..\Cortico"
node bin\cortico.mjs mybot > cortico_out.txt 2>&1
endlocal
