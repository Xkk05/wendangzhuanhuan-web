# 宝塔 Docker 部署说明

这份说明适用于把当前项目以“前端 + 后端”两容器方式部署到宝塔面板管理的 Docker 服务器。

当前提供的是国内源加速版部署包，后端镜像构建时会优先使用国内 Debian 镜像源，加快宝塔服务器上的首次构建速度。

## 部署结果

- 前端容器：`converter-frontend`
- 后端容器：`converter-backend`
- 对外访问端口：`3016`
- 后端仅在 Docker 内网暴露，不直接映射公网端口
- 上传、下载、日志持久化目录：`./docker-data/backend`

## 服务器要求

- 已安装宝塔面板
- 已安装宝塔 Docker 管理器
- 服务器可联网拉取镜像与安装依赖
- 推荐内存至少 `4G`
- 推荐磁盘至少预留 `10G+`

后端镜像会安装：

- `LibreOffice`
- `Chromium`
- `ffmpeg`
- 常见字体

首次构建会比较慢，这是正常的。

## 推荐目录

把项目放到例如下面的目录：

```bash
/www/wwwroot/converter-app
```

## 部署文件

本项目已提供生产部署文件：

- `docker-compose.baota.yml`

## 方式一：宝塔面板里直接部署

1. 将整个项目上传到服务器目录，例如 `/www/wwwroot/converter-app`
2. 在宝塔 Docker 管理器中进入该目录
3. 选择 `docker-compose.baota.yml`
4. 执行构建并启动

如果宝塔界面需要命令，使用：

```bash
docker compose -f docker-compose.baota.yml up -d --build
```

## 方式二：SSH 命令部署

进入项目目录：

```bash
cd /www/wwwroot/converter-app
```

启动：

```bash
docker compose -f docker-compose.baota.yml up -d --build
```

查看状态：

```bash
docker compose -f docker-compose.baota.yml ps
```

查看日志：

```bash
docker compose -f docker-compose.baota.yml logs -f
```

停止：

```bash
docker compose -f docker-compose.baota.yml down
```

## 宝塔站点反向代理

容器启动后，前端会监听服务器本机：

```text
127.0.0.1:3016
```

你可以在宝塔网站里：

1. 新建一个站点，例如 `convert.example.com`
2. 配置反向代理到：

```text
http://127.0.0.1:3016
```

因为前端容器里的 Nginx 已经处理了：

- `/`
- `/api/`
- `/downloads/`

所以宝塔层只要代理到 `3016` 即可，不需要再额外拆前后端代理。

## 数据持久化

后端数据会保存在：

```text
./docker-data/backend
```

对应内容包括：

- 上传文件
- 转换结果
- 日志

如果你迁移服务器，只要带上这个目录即可。

## 更新发布

代码更新后，在项目目录执行：

```bash
docker compose -f docker-compose.baota.yml up -d --build
```

## 常见问题

### 1. 构建很慢

首次构建需要安装大量系统依赖，属于正常现象。

### 2. 前端能打开，但转换失败

先看后端日志：

```bash
docker compose -f docker-compose.baota.yml logs -f backend
```

再确认健康检查是否通过：

```bash
docker compose -f docker-compose.baota.yml ps
```

### 3. 上传大文件失败

前端容器 Nginx 已配置：

```nginx
client_max_body_size 200m;
```

如果还需要更大，可以调整：

- `docker/nginx/default.conf`

### 4. 域名已配置，但打不开

检查：

- 宝塔站点是否反代到了 `127.0.0.1:3016`
- 服务器防火墙是否放行 `80/443`
- 容器是否正常运行

## 当前部署架构说明

浏览器请求路径：

1. 用户访问宝塔站点域名
2. 宝塔反向代理到 `converter-frontend:3016`
3. 前端容器内 Nginx 将 `/api` 和 `/downloads` 转发到后端容器
4. 后端 FastAPI 执行转换并返回结果

## 建议

正式上线前建议你在服务器上至少验证一次：

1. 首页是否能打开
2. 任意上传一个小文件能否转换
3. 转换结果能否下载
4. 登录相关接口是否符合你的线上预期
