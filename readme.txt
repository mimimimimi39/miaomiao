========================================
  mimi QQ 机器人  使用说明
========================================

一、快速开始
----------------------------------------
启动：双击 <AiQQ>\start_cortico.bat
      （新版 NapCat 无需 UAC，不再弹管理员窗口）
停止：双击 <AiQQ>\stop_cortico.bat

管理界面：
  Cortico  WebUI   http://127.0.0.1:7788/
  NapCat   WebUI   http://127.0.0.1:6099/  （token 见 NapCat\napcat\config\webui.json）

首次/掉线登录：
  二维码图片  <AiQQ>\NapCat\napcat\cache\qrcode.png
  （掉线时二维码守护会自动弹出最新的一张）


二、目录结构
----------------------------------------
AiQQ\
├─ Cortico\                 主程序（框架 + 插件 + 数据）
│   ├─ deployments\mybot\    配置、人设、记忆、画作
│   └─ extensions\           插件（含补丁版 qq-final / image）
├─ NapCat\                  协议端（Node 版，自带 QQ 内核）
│   ├─ napcat.bat            NapCat 启动脚本
│   └─ napcat\config\        NapCat 配置（端口/bypass/WebUI）
├─ tools\                   运维工具（桥接/GIF/二维码守护/迁移）
├─ docs\                    迁移与补丁说明
├─ backups\                 关键备份（插件补丁、配置、人设）
├─ files\                   收到的文件（新版默认目录）
├─ start_cortico.bat        一键启动
├─ stop_cortico.bat         一键停止
└─ readme.txt               本文件


三、重要修改记录（本次迁移后）
----------------------------------------
【协议端】
  NapCat 换成社区 fork 的 Node 版（自带 QQ 内核）：
  - 不再注入系统 QQ，彻底避开「文件已损坏」
  - 不需要 UAC/管理员权限
  - 配置文件在 NapCat\napcat\config\

【思考模式（重点）】
  指令：私聊或群里对她说 //0 //1 //2 //3
    //0 = none（不思考，最快）
    //1 = low
    //2 = high
    //3 = max
  - 只影响「QQ 对话回复」，说说/空间评论/主动搭话等固定为 high
  - 思考模式记录文件（重点目录）：
      <AiQQ>\Cortico\deployments\mybot\data\conv-effort.json
  - Provider 默认值（非对话行为）：
      <AiQQ>\Cortico\deployments\providers\mimi\config.json
      字段 spec.reasoningEffort

【群发言模式】
  主人对她说「你在X群安静点」→ 只收 @ 消息（含通知类全部不推）
  主人说「在X群自由发言」→ 不 @ 也会收到，3 秒静默后按语境接话
  记录文件：data\free-groups.json（groups=自由，muted=安静）

【空间评论自动回复】
  - 自动读说说正文再回复
  - 公开空间约束：不露骨、不提性、不写 QQ 号
  - 重启不会重复回复（repliedComments 已持久化）
  - 楼中楼也会回复，并带上级评论上下文

【表情包收藏】
  - 只有 VLM 明确识别出情绪时才收藏
  - 情绪「未知」/无法判断 → 跳过不收藏

【其他限制】
  - 图片下载上限 2MB（防请求体超限 413）
  - web_fetch 网页正文默认 4000 字符（上限 8000）


四、配置与数据路径
----------------------------------------
用途                        路径
-------------------------  -------------------------------------------------------------
主配置（开关/白名单/频率）     <AiQQ>\Cortico\deployments\mybot\config.json
人设（说话方式/规则）          <AiQQ>\Cortico\deployments\mybot\workspace\CONSTITUTION.md
模型端点（DeepSeek）           <AiQQ>\Cortico\deployments\providers\mimi\config.json
DeepSeek 密钥                  <AiQQ>\Cortico\deployments\providers\mimi\.env
出图/视频/搜索密钥             <AiQQ>\Cortico\deployments\mybot\.env
思考模式记录（//N）            <AiQQ>\Cortico\deployments\mybot\data\conv-effort.json
群模式记录                     <AiQQ>\Cortico\deployments\mybot\data\free-groups.json
聊天记忆 / 运行状态            <AiQQ>\Cortico\deployments\mybot\data\
她画的图                       <AiQQ>\Cortico\deployments\mybot\data\images\
收到的文件                     <AiQQ>\files\
NapCat 配置                    <AiQQ>\NapCat\napcat\config\
NapCat 日志                    <AiQQ>\Cortico\napcat_out.txt
Cortico 日志                   <AiQQ>\Cortico\cortico_out.txt
空间桥接日志                   <AiQQ>\tools\qzone_web.log


五、常见问题
----------------------------------------
Q: 掉线了怎么办？
   看 NapCat\napcat\cache\qrcode.png（守护会自动弹出），扫码登录。

Q: 想让她换说话风格？
   改 workspace\CONSTITUTION.md，保存后重启 Cortico。

Q: 想清除短期记忆（对话上下文）？
   WebUI → 存储 → 「主session（当前对话上下文）」→ 清除
   或：curl.exe -s --noproxy "*" -X POST "http://127.0.0.1:7788/api/storage/clear?key=session"

Q: 空间评论/说说突然不灵了？
   先确认 NapCat 在线（3000 端口），再重启桥接：
   cd <AiQQ>\tools && python qzone_web.py

Q: 怎么迁移到别的电脑？
   见 docs\迁移到Windows10.md


六、功能一览
----------------------------------------
- 私聊所有人；群聊只回 @；自由群按语境接话
- 主人长文/访客礼貌简短；访客复杂请求先请示主人
- 识图、看视频、联网搜索、读网页、引用消息
- 画图（gpt-image-2.6，Q 版）/ 视频（Grok Imagine，默认 1080p）
- 表情包（懂情绪才收）、语音、文件收发、群管理
- QQ 空间：发说说/回评论/回 @/自主评论
- 定时主动搭话、AI 作息（00:00 睡 / 08:00 起）、提醒、日记、好感度
- 思考模式 //0~//3（仅对话）
