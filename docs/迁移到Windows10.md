# 迁移到 Windows 10 主机（mimi / AiQQ）

## 一、目标机准备

| 依赖 | 版本 / 说明 |
|---|---|
| 系统 | Windows 10 64 位（Win10 1903+） |
| Node.js | **22 或更高**（Cortico 要求；装到 PATH） |
| pnpm | `npm i -g pnpm`（用于 Cortico 依赖，若整包迁移可跳过） |
| Python | **3.10+**，并安装 Pillow（`pip install pillow`）——桥接与 GIF 拆帧用 |
| QQ NT | 与当前同版本（NapCat 依赖 QQ NT 客户端，注册表需能查到卸载路径） |
| 可用端口 | 3000/3001（NapCat）、7788（WebUI）、8090（空间桥接）、6099（NapCat WebUI） |

> 目标机需要能访问：api.deepseek.com（主模型）、hynu.horizoncode.cn（画图）、api.smilecodex.space（视频）、QQ 网络。

## 二、迁移包内容

用 `tools\pack_transfer.ps1` 打包，包含：

- `Cortico\`（源码 + 扩展补丁 + deployments 配置 + workspace 人设/笔记 + data/images 她的画）
- `NapCat\`（协议端二进制 + 配置；不含 logs/cache）
- `tools\`（桥接、GIF 拆帧、二维码守护、重启脚本）
- `docs\`、`readme.txt`、`start_cortico.bat`、`stop_cortico.bat`

**默认不打包**（体积/缓存，可重建）：
- `Cortico\node_modules`（3GB+，目标机 `pnpm install` 重装）
- `Cortico\deployments\mybot\data\media`（聊天附件缓存 570MB）
- `Cortico\deployments\mybot\data\runs`（运行日志）
- `NapCat\logs`、`NapCat\cache`（日志/二维码缓存）
- `backups\`（历史备份，按需单独拷）

## 三、迁移步骤

1. 停服务：双击 `stop_cortico.bat`，并关闭 NapCat 的「管理员: powershell.exe」窗口 / 小号 QQ。
2. 打包：右键 `tools\pack_transfer.ps1` → 用 PowerShell 运行，或：
   ```powershell
   powershell -ExecutionPolicy Bypass -File <AiQQ>\tools\pack_transfer.ps1 -Dest "<AiQQ>_transfer"
   ```
   （默认目标 `<AiQQ>_transfer`；想带 node_modules 加 `-WithNodeModules`，想带聊天附件缓存加 `-WithMedia`）
3. 把 `D:\AiQQ_transfer` 拷贝到目标机（U 盘 / 局域网）。
4. 目标机解压到 **同路径** `<AiQQ>`（推荐）；若不同路径：
   ```powershell
   python tools\rebind_paths.py "<AiQQ>" "D:\AiQQ"
   ```
5. 目标机安装 Node 22+ / Python 3.10+ + Pillow / QQ NT。
6. 若迁移包未带 `node_modules`：
   ```powershell
   cd <AiQQ>\Cortico
   pnpm install
   ```
   （pnpm install 会覆盖 qq-final 补丁——迁移包已包含打好补丁的扩展；重装后需按 `docs\补丁清单.md` 重新打补丁）
7. 启动：双击 `start_cortico.bat`，UAC 点「是」。
8. **扫码登录小号**（登录态不随迁移走）：二维码会自动弹出（或从 `NapCat\cache\qrcode.png` 手动打开）。
9. 打开 WebUI `http://127.0.0.1:7788/` 确认在线。

## 四、注意事项

- `.env` 里有 API Key，**不要上传网盘/公开仓库**，用 U 盘或局域网直传。
- `deployments\mybot\data\images` 是她画的图（约 400MB），迁移包默认包含；不要就删掉。
- `data\media` 是聊天图片/语音缓存，不迁移不影响运行（历史图在上下文里只剩文字说明）。
- NapCat 登录态与本机 QQ 绑定，迁移后必须重新扫码。
- 目标机若没有 `C:\AAA\!tools`（GIF 拆帧用到 `tools\gif_frames.py` 的路径在插件里写死），请运行 `rebind_paths.py`，或保持同路径。
- 首次启动若提示扩展导入失败，先看 `Cortico\cortico_out.txt` 的报错行。

## 五、回滚

迁移前保留旧机 `<AiQQ>` 原样不动；新机跑通后再清理旧机即可。
