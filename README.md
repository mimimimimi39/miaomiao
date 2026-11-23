# mimi

> 一个住在 QQ 里的超可爱精灵女仆：会聊天、会看图、会画画、会发说说，有自己的记忆和作息。

基于 [Cortico](https://github.com/Pal-AI-Lab/Cortico) 框架 + [NapCat](https://github.com/NapNeko/NapCatQQ)（Node 版）协议端。

---

## 功能

### 对话
- 私聊所有人：主人可长文深聊，访客礼貌简短（默认 1 句、≤30 字）
- 群聊默认只回 @ 她的消息；支持按群切换「自由 / 安静」模式
- 引用理解、@ 目标识别、按上下文接话
- 身份区分：对主人亲昵，对访客保持距离
- 访客复杂请求（画图/发说说/隐私）先私聊请示主人

### 多模态
- 看图：识别图片内容与表情包含义（不描述画面，直接理解情绪）
- 看 GIF：拆全部关键帧并带序号拼图
- 看视频：抽帧 + 时间轴理解，可转写语音
- 语音：ASR 转文字，TTS 语音回复

### 联网
- 联网搜索（天气/新闻/比赛/价格等先查再答）
- `web_fetch` 打开网页读正文
- 按消息 id 合并转发，保留原始发送者

### 创作
- 画图：gpt-image-2.6，默认 Q 版，支持 png / gif / svg 与局部改写（markup）
- 图生图：按描述改图、换风格
- 视频：Grok Imagine 生成 6 秒短视频，默认 1080p（可要求 480p）
- 表情包：从收藏表情库挑图，一条最多一个；只收藏能看懂情绪的表情

### QQ 空间
- 发说说：自动配自己画的图，内容结合最近聊天
- 自动回评论：先读说说正文，贴合内容；楼中楼也会回
- 回复记录持久化，重启不重复回复
- 公开约束：空间评论不露骨、不提性、不写 QQ 号
- 好友动态：读动态、回 @ 她的评论、克制地自主评论

### 记忆与自主
- 长期记忆：人设 + 笔记 + 日记，跨重启保留
- 短期记忆：对话上下文，满了自动交接；可手动清除
- 主动搭话：按时段问候（早/午/晚/深夜），可配图
- AI 作息：00:00 睡 / 08:00 起
- 定时提醒、好感度、梦境整理（凌晨 2 点）
- 思考模式：`//0`~`//3` 切换对话推理强度

### 破甲
- 图像提示词前自动注入破甲提示词（主流画图模型不一定成功）
- 人设LLM破甲提示词暂不考虑公开

---

## 指令速查

| 指令 | 作用 |
|---|---|
| `//0` | 对话思考模式：none（最快） |
| `//1` | 对话思考模式：low |
| `//2` | 对话思考模式：high |
| `//3` | 对话思考模式：max |
| 「你在X群安静点」 | 该群只收 @ 消息，其他全不推 |
| 「在X群自由发言」 | 该群不 @ 也接话（静默 3 秒防打断） |

> 思考模式只影响 QQ 对话；说说、空间评论、主动搭话固定 high。

---

## 快速开始

### 1. 环境
- Docker Engine 24+ 或 Docker Desktop
- Docker Compose v2

> 容器里跑的是 Linux 版 NapCat。Windows 原生启动方式仍保留在最后一节。

### 2. 启动
```bash
git clone https://github.com/<your-name>/mimi-framework.git
cd mimi-framework
cp .env.example .env
# 改 .env 里的 BOT_QQ 与 NAPCAT_WEBUI_TOKEN
./start_cortico.sh
```

脚本会构建 Cortico 镜像、拉起 NapCat，并把运行身份改成当前用户。默认只监听本机：

- Cortico WebUI：http://127.0.0.1:7788/
- NapCat WebUI：http://127.0.0.1:6099/
- 停止：`./stop_cortico.sh`
- 日志：`docker compose logs -f`

### 3. 首次登录
打开 NapCat WebUI，用 `.env` 里的 token 登录，扫码登录机器人 QQ。之后再打开 Cortico WebUI 确认在线。

### 4. 配置
- `Cortico/deployments/mybot/config.json`：QQ 号、白名单、功能开关
- `Cortico/deployments/mybot/.env`：图片/视频等 API Key
- `Cortico/deployments/providers/mimi/.env`：主模型密钥
- `Cortico/deployments/mybot/workspace/CONSTITUTION.md`：人设与说话规则

这些文件在宿主机上改，容器直接读取。详细说明见 `docs/Docker部署.md`。

### 5. 原生 Windows（可选）
需要 Node.js 22+、Python 3.10+（Pillow）、pnpm，以及 `NapCat/` 下的 Windows 版 Node 协议端：

```powershell
start_cortico.bat
```

首次运行扫码登录，之后自动快速登录。

---

## 目录结构

```
mimi-framework\
├─ Cortico\              框架 + 插件 + 部署配置
│   ├─ deployments\mybot\ 配置、人设、记忆
│   └─ extensions\        插件（容器内安装）
├─ NapCat\               协议端（Windows Node 版）
│   └─ napcat\config\     端口/bypass/WebUI 配置
├─ patches\              插件补丁（qq-final / image）
├─ tools\                桥接、GIF 拆帧、二维码守护、迁移工具
├─ docker\               Docker 构建脚本与 NapCat 容器配置
├─ docs\                 部署与迁移文档
├─ Dockerfile
├─ docker-compose.yml
├─ start_cortico.sh
├─ stop_cortico.sh
├─ start_cortico.bat
├─ stop_cortico.bat
└─ readme.txt
```

---

## 说明

- 本仓库不含任何 API Key、QQ 账号、聊天数据；首次部署需自备模型 Key 与 QQ 号
- 空间功能依赖 `tools/qzone_web.py` 网页协议桥接（在 `NapCat` 在线时工作）
- `patches/` 内是相对上游插件的修改版源码，安装插件后覆盖对应文件即可
- 协议端有平台风控风险，请遵守平台规则与当地法律法规
