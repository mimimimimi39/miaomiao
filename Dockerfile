# syntax=docker/dockerfile:1.7

FROM node:22-bookworm-slim AS build

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        libcairo2-dev \
        libgif-dev \
        libjpeg-dev \
        libpango1.0-dev \
        librsvg2-dev \
        pkg-config \
        python3 \
    && rm -rf /var/lib/apt/lists/*

RUN corepack enable && corepack prepare pnpm@11.28.6 --activate

WORKDIR /app/Cortico

COPY Cortico/package.json Cortico/pnpm-lock.yaml Cortico/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

COPY Cortico/ ./
COPY docker/extensions/ ./extensions/
RUN cd extensions && pnpm install --frozen-lockfile

COPY patches/ /app/patches/
RUN set -eux; \
    cp -a /app/patches/qq-final/src/. "$(readlink -f extensions/node_modules/cortico-world-qq-final)/src/"; \
    cp -a /app/patches/image/src/. "$(readlink -f extensions/node_modules/cortico-world-image)/src/"

RUN pnpm build:web


FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production \
    TZ=Asia/Shanghai \
    CORTICO_OPEN_BROWSER=0 \
    CORTICO_START_PAUSED=0

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        git \
        libcairo2 \
        libgif7 \
        libjpeg62-turbo \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        librsvg2-2 \
        python3 \
        python3-pil \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3 /usr/local/bin/python

COPY --from=build /app /app
COPY docker/entrypoint.sh /usr/local/bin/mimi-entrypoint.sh
RUN chmod +x /usr/local/bin/mimi-entrypoint.sh

RUN corepack enable && corepack prepare pnpm@11.28.6 --activate

WORKDIR /app/Cortico
EXPOSE 7788

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD node -e "fetch('http://127.0.0.1:' + (process.env.CORTICO_PORT || '7788') + '/').then((r) => process.exit(r.ok ? 0 : 1)).catch(() => process.exit(1))"

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/mimi-entrypoint.sh"]
