# ============================================================
# 多阶段构建共用镜像：Web 主站 / 爬虫接口 / WebSocket 三个服务共用一个镜像，
# 只是启动命令不同——镜像一致、进程不同，这是容器化部署的常规做法。
# 构建上下文是项目根目录（见 docker-compose.yml 里的 context: ..）
# ============================================================
FROM python:3.12-slim

WORKDIR /app

# 先只拷依赖清单再装依赖：利用 Docker 层缓存，代码改动不用重装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再拷项目代码（Code/ 目录：App.py、config.py、templates/、static/ ...）
COPY Code/ .

EXPOSE 5000 8000 8888

# 默认启动 Web 主站（waitress）；其他服务在 docker-compose.yml 里覆盖 command
CMD ["python", "-u", "start_server.py"]
