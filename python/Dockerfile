FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY baidu_pan_player.py .

# 暴露端口
EXPOSE 5000

# 设置环境变量
ENV HOST=0.0.0.0
ENV PORT=5000
ENV DEBUG=false
ENV PYTHONUNBUFFERED=1

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health').raise_for_status()"

# 启动应用
CMD ["python", "baidu_pan_player.py"]
