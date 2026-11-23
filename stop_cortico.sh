#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

docker compose down "$@"

echo "mimi 已停止。数据仍在 Cortico/deployments 与 docker/napcat 下。"
