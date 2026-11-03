# syntax=docker/dockerfile:1

FROM node:26-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
# Node no longer ships Corepack (since 25): pnpm is installed at the version package.json pins, so the two never drift.
RUN npm install --global "pnpm@$(node -p "require('./package.json').packageManager.split('@')[1].split('+')[0]")"
RUN pnpm install --frozen-lockfile

FROM deps AS build
COPY . .
RUN pnpm build

# Local development (docker-compose.override.yaml): the Vite dev server, with the sources mounted over /app
# so an edit shows up in the browser straight away. Not an image to ship.
FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["pnpm", "exec", "vite", "--host", "0.0.0.0"]

# nginxinc/nginx-unprivileged already runs as the unprivileged `nginx` user
# (uid 101) and listens on 8080 instead of 80, so no extra USER/port setup
# is required to get a non-root container.
FROM nginxinc/nginx-unprivileged:alpine AS runtime
# The base image only gets rebuilt now and then: pull in the Alpine fixes published since (openssl,
# zlib, musl...). It needs root, which the base image doesn't run as - dropped again right after.
# A build cache keeps the result of the upgrade as long as this line does not change: when Trivy
# reports a fixable critical in the frontend image, bring this date forward to run the upgrade again.
ARG APK_UPGRADE_AS_OF=2026-11-03
USER root
RUN echo "Alpine fixes as of ${APK_UPGRADE_AS_OF}" && apk upgrade --no-cache
COPY --chown=nginx:nginx docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=nginx:nginx --from=build /app/dist /usr/share/nginx/html
# Explicit rather than inherited from the base image: same user as before (nginx, uid 101), but
# visible to scanners (Trivy DS-0002 can't see an inherited USER).
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
