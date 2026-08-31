# ACAN Studio 网页测试版

网页测试版面向 Windows、macOS 和手机浏览器，第一阶段只处理无需登录即可播放的公开视频。它不会读取或接收浏览器 Cookie，也不支持会员、付费、DRM、直播、合集或用户主页。

## 当前功能

- 粘贴视频链接或包含链接的分享文案
- 后台单视频下载、断点续传、音画合并
- 网页实时显示进度、速度和预计剩余时间
- 处理完成后直接下载结果
- 任务取消、并发上限和结果自动清理
- 体验码保护、平台域名白名单和内网地址拦截

## 本地启动

需要 Python 3.11 以上、yt-dlp、Deno 和 FFmpeg：

```bash
python3 -m venv .venv-web
source .venv-web/bin/activate
pip install -r requirements-web.txt
export PYTHONPATH="$PWD/web"
export ACAN_WEB_DATA_DIR="$PWD/.acan-web-data"
export ACAN_WEB_ACCESS_CODE="设置一个体验码"
uvicorn acan_web.app:app --host 127.0.0.1 --port 8080
```

然后打开 `http://127.0.0.1:8080`。

## Docker 启动

```bash
export ACAN_WEB_ACCESS_CODE="设置一个不容易猜到的体验码"
docker compose -f docker-compose.web.yml up --build
```

服务默认监听 `8080` 端口。公开部署前必须配置 HTTPS、体验码和服务器防火墙，建议先只邀请少量朋友测试。

## 可配置项目

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ACAN_WEB_ACCESS_CODE` | 空 | 创建任务所需体验码；公开部署必须设置 |
| `ACAN_WEB_DATA_DIR` | `/data/acan-web` | 临时结果目录 |
| `ACAN_WEB_MAX_WORKERS` | `2` | 同时处理任务数，代码上限为 4 |
| `ACAN_WEB_MAX_PENDING` | `8` | 运行和排队任务总数 |
| `ACAN_WEB_RETENTION_SECONDS` | `7200` | 结果保留时间，最低 15 分钟 |
| `ACAN_WEB_MAX_FILESIZE` | `2G` | 单个视频大小限制 |
| `ACAN_WEB_YTDLP` | 自动查找 | 自定义 yt-dlp 路径 |

## 上线前注意

- 网页视频处理会消耗较多服务器带宽、存储和 CPU；公开测试时应限制人数和文件大小。
- 结果目录属于临时数据，部署时需要独立磁盘空间监控和定时清理。
- 不要把 Cookie、账号密码或用户隐私信息传到网页后台。
- YouTube 可能根据服务器网络出口要求真人验证；网页测试版不会上传或共用个人 Cookie，遇到此提示请使用桌面版。
- 下载和保存内容必须遵守平台条款、版权规定和内容发布者授权。
- 生产环境应放在支持长连接和大文件传输的 HTTPS 反向代理后面，并设置上传/下载超时。
