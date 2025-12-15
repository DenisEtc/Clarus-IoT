# ---- build web (Vite) ----
FROM node:20-alpine AS webbuilder
WORKDIR /web

COPY web/package.json web/package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY web/ ./
RUN npm run build

# ---- nginx serve ----
FROM nginx:alpine

# 1) Удаляем дефолтные и старые конфиги, чтобы не было "левого" app.conf
RUN rm -f /etc/nginx/conf.d/*.conf

# 2) Кладём наши конфиги
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf
COPY deploy/nginx/conf.d/default.conf /etc/nginx/conf.d/default.conf

# 3) Кладём фронт
COPY --from=webbuilder /web/dist /usr/share/nginx/html
