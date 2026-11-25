#!/bin/sh
set -eu

cd /app/Cortico

BOT="${CORTICO_BOT:-mybot}"
HOST="${CORTICO_HOST:-0.0.0.0}"
PORT="${CORTICO_PORT:-7788}"
# 容器启动和重启后直接投递事件；上游默认 paused=1，会一直停在暂停状态。
export CORTICO_START_PAUSED="${CORTICO_START_PAUSED:-0}"

QZONE_LOG="${QZONE_LOG:-/app/Cortico/deployments/$BOT/data/qzone_web.log}"
export QZONE_LOG
mkdir -p "$(dirname "$QZONE_LOG")"

qpid=""
if [ "${QZONE_BRIDGE_ENABLED:-1}" = "1" ]; then
  python3 /app/tools/qzone_web.py &
  qpid=$!
fi

node bin/cortico.mjs "$BOT" "--host=$HOST" "--port=$PORT" "$@" &
cpid=$!

stop_children() {
  kill -TERM "$cpid" 2>/dev/null || true
  if [ -n "$qpid" ]; then
    kill -TERM "$qpid" 2>/dev/null || true
  fi
}
trap stop_children TERM INT

code=0
wait "$cpid" || code=$?

stop_children
wait "$cpid" 2>/dev/null || true
if [ -n "$qpid" ]; then
  wait "$qpid" 2>/dev/null || true
fi
exit "$code"
