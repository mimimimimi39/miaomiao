# NapCat 迁移完成记录（2026-11-23）

## 结果

✅ **已解决**：迁移后 NapCat 无法启动的问题。

## 根因

原 NapCat（4.18.42 Shell 注入模式）在目标机 + QQ 9.9.32 环境下，
注入时被 QQ 完整性校验拦截（「文件已损坏」），与旧机环境差异无法复刻。

NapCat 官方仓库已删除（删库跑路），改用社区 fork：

- 仓库：https://github.com/Creep-debug/NapCatQQ
- 下载：`NapCat.Shell.Windows.Node.zip`（2026-11-10 发布，118MB）

## 新方案

新版 NapCat 是 **Node 版（自带 QQ 内核）**，不需要注入系统 QQ，
直接运行 `napcat.bat` 即可（`node.exe` + `index.js` + 内置 QQNT）。

### 当前目录结构

```
<AiQQ>\
├─ NapCat\                  ← 新版（Node 版，自带 QQ 内核）
│   ├─ napcat.bat           启动脚本（node.exe index.js）
│   ├─ node.exe
│   ├─ index.js
│   └─ napcat\              核心
│       ├─ napcat.mjs
│       ├─ config\          配置（已迁移旧配置）
│       └─ cache\qrcode.png 登录二维码
├─ NapCat_old_4.18.42\      ← 旧版（注入模式，已弃用，可删）
└─ ...
```

### 配置

已从旧版迁移：
- `napcat\config\onebot11_<BOT_QQ>.json`（端口 3000/3001）
- `napcat\config\napcat_<BOT_QQ>.json`（bypass 反检测全开）
- `napcat\config\napcat.json`（全局默认）
- `napcat\config\webui.json`（WebUI token）

### 启动

- 一键启动：`start_cortico.bat`（已更新为 NapCat Node 版，无需 UAC）
- 单独启动 NapCat：
  ```
  cd <AiQQ>\NapCat
  napcat.bat
  ```
- 二维码：`<AiQQ>\NapCat\napcat\cache\qrcode.png`
- 首次需扫码登录（快速登录失效后自动出二维码）

### 验证（2026-11-23 16:36）

- NapCat 3000/3001 ✅
- mimi（<BOT_QQ>）登录 ✅
- 消息收发 ✅（HANDLE_IN / qq_send）
- 空间桥接 ✅（能读说说）
- 图片/文件待日常使用验证

## 备注

- 新 NapCat 会尝试快速登录，登录态失效时自动生成二维码
- 二维码有效期约 2 分钟，掉线时二维码守护会自动弹出（路径已更新）
- 旧版目录保留在 `NapCat_old_4.18.42`，确认稳定后可删除
