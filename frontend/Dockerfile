FROM docker.m.daocloud.io/node:20-alpine AS build

WORKDIR /app/frontend
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
RUN npm config set registry ${NPM_CONFIG_REGISTRY}

COPY frontend/package.json frontend/package-lock.json ./
ARG VITE_API_BASE_URL=
ARG VITE_OAUTH_CALLBACK_URL=
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_OAUTH_CALLBACK_URL=${VITE_OAUTH_CALLBACK_URL}

RUN npm ci

COPY frontend/ ./

RUN npm run build

FROM docker.m.daocloud.io/nginx:1.27-alpine

COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
