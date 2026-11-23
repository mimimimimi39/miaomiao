# 用 Docker Compose 部署 mimi

Docker 版把 Cortico、QQ 空间桥接和 NapCat 分成两个容器：

| 服务 | 内容 | 默认端口 |
|---|---|---|
| `cortico` | Cortico、`tools/qzone_web.py`、Python/Pillow、ffmpeg | 7788（WebUI） |
| `napcat` | Linux 版 NapCat（OneBot v11） | 6099（WebUI） |

两个 WebUI 默认只绑 `127.0.0.1`。OneBot 的 3000/3001 只在 Compose 内部网络开放，不映射到宿主机。

## 一、准备

需要 Docker Engine 24+ 与 Docker Compose v2。

```bash
git clone https://github.com/<your-name>/mimi-framework.git
cd mimi-framework
cp .env.example .env
```

编辑 `.env`：

| 变量 | 作用 |
|---|---|
| `BOT_QQ` | 协议端要登录的 QQ 号，仅作初始值；仍要在 NapCat WebUI 扫码 |
| `NAPCAT_WEBUI_TOKEN` | NapCat WebUI 的登录口令，必须换掉 |
| `MIMI_BIND_HOST` | 两个 WebUI 的监听地址；默认 `127.0.0.1` |
| `CORTICO_PORT` | Cortico WebUI 的宿主机端口 |
| `NAPCAT_WEBUI_PORT` | NapCat WebUI 的宿主机端口 |
| `NAPCAT_IMAGE` | NapCat 镜像，可固定版本，例如 `mlikiowa/napcat-docker:v4.18.28` |

## 二、启动

```bash
./start_cortico.sh
```

脚本做四件事：缺少 `.env` 时从 `.env.example` 生成并随机化 NapCat token；把 `NAPCAT_UID/GID`、`MIMI_UID/GID` 设为当前用户；按 `BOT_QQ` 生成 `docker/napcat/config/onebot11_<QQ>.json`；执行 `docker compose up -d --build`。

首次启动会拉取 NapCat 镜像并构建 Cortico 镜像，需要访问 Docker Hub、npm registry 与系统软件源。

打开 `http://127.0.0.1:6099/`，输入 `NAPCAT_WEBUI_TOKEN`，扫码登录 QQ。登录成功后打开 `http://127.0.0.1:7788/`，确认 Cortico 在线。

## 三、密钥与配置

宿主机上的 `Cortico/deployments/` 直接挂进容器，改完保存即可。密钥按 Cortico 的约定分开放：

| 文件 | 内容 |
|---|---|
| `Cortico/deployments/providers/mimi/.env` | `DEEPSEEK_API_KEY` |
| `Cortico/deployments/providers/grok/.env` | `GROK_API_KEY` |
| `Cortico/deployments/mybot/.env` | `IMAGE_API_KEY` 等 World 密钥 |
| `Cortico/deployments/mybot/config.json` | QQ 白名单、功能开关、画图模型 |
| `Cortico/deployments/mybot/workspace/CONSTITUTION.md` | 人设 |

这些密钥文件不进 git，也不进镜像；`config.json` 与人设随仓库管理。

## 四、数据与目录

| 路径 | 内容 |
|---|---|
| `Cortico/deployments/mybot/data/` | 会话、事件、记忆索引、画作、运行日志 |
| `Cortico/deployments/mybot/workspace/` | 人设与长期记忆 |
| `docker/napcat/config/` | NapCat 配置；`onebot11_<QQ>.json` 由启动脚本按 `.env` 的 `BOT_QQ` 生成 |
| `docker/napcat/qq/` | QQ 登录态 |
| `docker/napcat/logs/` | NapCat 日志 |
| `docker/napcat/plugins/` | NapCat 插件 |

备份 `Cortico/deployments/` 与 `docker/napcat/` 即可。删除 `docker/napcat/qq/` 会要求重新扫码。

Cortico 插件（`cortico-bot-continuity`、`cortico-world-qq-final`、`cortico-world-image`、`cortico-world-deepseek-usage`、`cortico-provider-deepseek`）在构建镜像时按固定版本安装，并覆盖 `patches/` 里的修改。它们属于镜像，不在宿主机目录里；升级或新增插件改 `docker/extensions/package.json` 后重新构建。WebUI 里临时装的扩展也会随容器重建消失。

## 五、脚本

| 脚本 | 作用 |
|---|---|
| `./start_cortico.sh` | 构建并后台启动 |
| `./stop_cortico.sh` | 停止并删除容器（保留数据） |
| `./tools/restart_napcat.sh` | 只重启 NapCat 并打印最近日志 |
| `NapCat/napcat.sh` | 仅当 `NapCat/` 换成 Linux/Node 构建时，直接运行 `NapCat/index.js` |

## 六、更新

```bash
git pull
docker compose build --pull
docker compose up -d
```

Cortico 的数据在宿主机，重建容器不会丢。

## 七、常见问题

**Cortico 连不上 WebSocket。** 确认 NapCat 已扫码登录，且 `docker/napcat/config/onebot11_<QQ>.json` 的 3001 正向 WS 服务处于启用状态。容器内地址固定为 `ws://napcat:3001`，由 `MIMI_NAPCAT_WS` 传给插件。

**NapCat 起不来。** `docker compose logs napcat`。Linux 容器需要 `NAPCAT_UID/GID` 与数据目录属主一致；脚本默认使用当前用户。

**二维码在哪。** NapCat WebUI 的登录页会显示二维码；也可以从容器日志里找。

**想让局域网访问 WebUI。** 把 `MIMI_BIND_HOST` 改成 `0.0.0.0`，同时设置防火墙。Cortico WebUI 没有内建身份认证，暴露前先放到带认证的反向代理后面。

**拉不到 Docker Hub 镜像。** 换 `NAPCAT_IMAGE` 为本地镜像或镜像代理地址。

## 八、与 Windows 原生版的差异

- Docker 版使用 Linux NapCat 容器，不再使用 `NapCat/` 里的 Windows 可执行文件。
- 原 Windows 启动脚本仍是 `start_cortico.bat` / `stop_cortico.bat`。
- 容器内的 GIF 拆帧脚本路径由 `MIMI_GIF_FRAMES` 指定；QQ 空间桥接的 NapCat 地址由 `QZONE_NAPCAT_URL` 指定。
- 镜像带 Python 与 Pillow，但不带本地 ASR 的 `venv_vox`。默认 `asr.mode=local` 在容器里无法拉起，需自行安装该环境，或在配置里改用云端 ASR。
