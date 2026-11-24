@echo off
setlocal
cd /d "%~dp0..\NapCat"
napcat.bat > "%~dp0..\Cortico\napcat_out.txt" 2>&1
endlocal
