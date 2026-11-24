@echo off
chcp 936 >nul
title mimi 刷新人设
echo ========================================
echo   mimi 一键刷新人设（不重启）
echo ========================================
echo.
echo 正在重载系统前缀（人设 + 工具表）...
curl -s --noproxy "*" -X POST http://127.0.0.1:7788/api/session/reload-prefix
echo.
echo ----------------------------------------
echo 完成：新人设已生效，当前对话保留。
echo （如没生效，确认 CONSTITUTION.md 已保存）
echo ----------------------------------------
pause
