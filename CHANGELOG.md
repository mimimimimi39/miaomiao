# Changelog

## v1.0.0 — 2026-11-24

首个公开 1.0 版本。

- 保留 Docker Compose 一键部署和 Windows 一键启动。
- 人设年龄统一为 18 岁，外观描述同步更新。
- 主人私聊新增 `//clear` / `//清空`：清空当前 session，保留系统前缀、日记和长期记忆。
- QZone 评论轮询跳过空 `tid`，避免 NapCat 时代失败记录反复报错。
- Windows 启动脚本改为仓库相对路径，不再依赖本机绝对路径；Node.js 从 PATH 读取。
- Windows 启动脚本不再依赖不存在的 `napcat_qr_watch.py`。
- 补充版本文件、变更记录和 README 的 1.0 说明。

## 更早版本

- 0.2.x：Cortico + NapCat 接入、人格/记忆/日记/图片/QZone/语音/群管理等功能逐步加入。
