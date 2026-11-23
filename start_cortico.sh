#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v docker >/dev/null 2>&1; then
  echo "找不到 docker。先安装 Docker Engine 或 Docker Desktop。" >&2
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "找不到 docker compose 插件。需要 Docker Compose v2。" >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  token="$(openssl rand -hex 16 2>/dev/null || date +%s%N)"
  sed -i.bak "s/^NAPCAT_WEBUI_TOKEN=.*/NAPCAT_WEBUI_TOKEN=${token}/" .env
  rm -f .env.bak
  echo "已生成 .env，NapCat WebUI 口令是 ${token}"
fi

read_env() {
  sed -n "s/^$1=//p" .env | tail -1
}

env_or() {
  value="$(read_env "$1")"
  if [ -n "$value" ]; then
    echo "$value"
  else
    echo "$2"
  fi
}

bot_qq="$(env_or BOT_QQ 10001)"
if [[ ! "$bot_qq" =~ ^[0-9]+$ ]]; then
  echo ".env 里的 BOT_QQ 必须是数字，当前是：${bot_qq}" >&2
  exit 1
fi

export NAPCAT_UID="${NAPCAT_UID:-$(id -u)}"
export NAPCAT_GID="${NAPCAT_GID:-$(id -g)}"
export MIMI_UID="${MIMI_UID:-$(id -u)}"
export MIMI_GID="${MIMI_GID:-$(id -g)}"

mkdir -p docker/napcat/config docker/napcat/qq docker/napcat/plugins docker/napcat/logs

# 仓库自带的 OneBot 配置按 NapCat 约定是 onebot11_<QQ>.json。
# 首次启动复制一份，之后改动不会被覆盖。
account_config="docker/napcat/config/onebot11_${bot_qq}.json"
if [ ! -f "$account_config" ]; then
  cp docker/napcat/config/onebot11_10001.json "$account_config"
fi

docker compose up -d --build "$@"

echo
echo "mimi 正在启动。"
echo "  Cortico  WebUI   http://$(env_or MIMI_BIND_HOST 127.0.0.1):$(env_or CORTICO_PORT 7788)/"
echo "  NapCat   WebUI   http://$(env_or MIMI_BIND_HOST 127.0.0.1):$(env_or NAPCAT_WEBUI_PORT 6099)/"
echo "  查看日志          docker compose logs -f"
echo
echo "首次运行在 NapCat WebUI 扫码登录 QQ；Cortico 的模型密钥填在 deployments 的 .env。"
