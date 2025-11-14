# 百度网盘播放地址提取服务 (Python实现)

## 功能说明

这是一个独立的Python服务，专门用于从百度网盘获取视频播放地址，直接调用百度网盘的`crack_video` API，并返回适合`com.fongmi.android.tv`影视客户端使用的播放信息。

### 核心特性

✅ **直接调用百度网盘API** - 无需AList等中间件  
✅ **使用crack_video接口** - 获取直接可播放的视频地址  
✅ **netdisk User-Agent** - 模拟百度网盘官方客户端  
✅ **适配影视客户端** - 返回格式符合com.fongmi.android.tv要求  
✅ **简单易用** - RESTful API，易于集成  

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python baidu_pan_player.py
```

默认运行在: `http://0.0.0.0:5000`

### 3. 环境变量配置（可选）

```bash
export HOST=0.0.0.0
export PORT=5000
export DEBUG=false
```

## API接口

### 1. 获取播放地址

**端点**: `/play`  
**方法**: `GET` 或 `POST`

#### 请求参数

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| cookie | string | ✅ | 百度网盘Cookie (BDUSS和STOKEN) |
| file_path | string | ⬜ | 文件路径，如: /视频/电影.mp4 |
| fs_id | string | ⬜ | 文件ID |
| share_url | string | ⬜ | 分享链接，如: https://pan.baidu.com/s/1xxxxx |
| pwd | string | ⬜ | 分享链接的提取码 |

**注意**: `file_path`、`fs_id`、`share_url` 三者至少提供一个

#### 响应格式

**成功响应**:
```json
{
  "parse": 0,
  "playUrl": "",
  "url": "https://d.pcs.baidu.com/file/xxxxx...",
  "header": {
    "User-Agent": "netdisk",
    "Referer": "https://pan.baidu.com"
  },
  "name": "电影.mp4",
  "size": 1234567890
}
```

**错误响应**:
```json
{
  "error": true,
  "message": "错误描述",
  "url": "",
  "parse": 0
}
```

#### 使用示例

**方式1: 通过文件路径获取 (GET)**

```bash
curl "http://localhost:5000/play?cookie=BDUSS=xxx;STOKEN=xxx&file_path=/视频/电影.mp4"
```

**方式2: 通过文件ID获取 (POST)**

```bash
curl -X POST http://localhost:5000/play \
  -H "Content-Type: application/json" \
  -d '{
    "cookie": "BDUSS=xxx; STOKEN=xxx",
    "fs_id": "123456789"
  }'
```

**方式3: 通过分享链接获取**

```bash
curl -X POST http://localhost:5000/play \
  -H "Content-Type: application/json" \
  -d '{
    "cookie": "BDUSS=xxx; STOKEN=xxx",
    "share_url": "https://pan.baidu.com/s/1xxxxx",
    "pwd": "1234"
  }'
```

### 2. 列出文件

**端点**: `/list`  
**方法**: `GET` 或 `POST`

#### 请求参数

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| cookie | string | ✅ | - | 百度网盘Cookie |
| dir | string | ⬜ | / | 目录路径 |
| page | int | ⬜ | 1 | 页码 |
| size | int | ⬜ | 100 | 每页数量 |

#### 示例

```bash
curl "http://localhost:5000/list?cookie=BDUSS=xxx;STOKEN=xxx&dir=/视频"
```

### 3. 健康检查

**端点**: `/health`  
**方法**: `GET`

```bash
curl http://localhost:5000/health
```

### 4. API信息

**端点**: `/info`  
**方法**: `GET`

```bash
curl http://localhost:5000/info
```

## 如何获取Cookie

### 方法1: 浏览器开发者工具

1. 打开百度网盘网页: https://pan.baidu.com
2. 登录你的账号
3. 按 `F12` 打开开发者工具
4. 切换到 `Network` (网络) 标签
5. 刷新页面 (`F5`)
6. 点击任意请求
7. 在 `Request Headers` 中找到 `Cookie`
8. 复制 `BDUSS` 和 `STOKEN` 的值

Cookie格式:
```
BDUSS=你的BDUSS值; STOKEN=你的STOKEN值
```

### 方法2: 浏览器Cookie管理器

1. Chrome: `chrome://settings/cookies`
2. 搜索: `baidu.com`
3. 找到并复制 `BDUSS` 和 `STOKEN`

## 与com.fongmi.android.tv集成

### 在影视客户端中配置

影视客户端可以调用此服务获取播放地址:

```
播放地址API: http://your-server:5000/play
```

### 客户端请求示例

```javascript
// 构建请求
const playUrl = 'http://your-server:5000/play';
const params = {
  cookie: 'BDUSS=xxx; STOKEN=xxx',
  file_path: '/视频/电影.mp4'
};

// 发送请求
fetch(playUrl, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(params)
})
.then(response => response.json())
.then(data => {
  if (!data.error) {
    // 使用返回的URL和headers播放视频
    playVideo(data.url, data.header);
  }
});
```

### 播放器使用

获取到的响应中包含:
- `url`: 视频播放地址
- `header`: 必需的HTTP headers (包含User-Agent: netdisk)

播放器在请求视频流时，必须带上这些headers:

```python
import requests

# 从API获取播放信息
play_info = {
  "url": "https://d.pcs.baidu.com/file/...",
  "header": {
    "User-Agent": "netdisk",
    "Referer": "https://pan.baidu.com"
  }
}

# 播放视频时使用这些headers
response = requests.get(
    play_info['url'], 
    headers=play_info['header'],
    stream=True
)
```

## Docker部署

### 创建Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY baidu_pan_player.py .

EXPOSE 5000

ENV HOST=0.0.0.0
ENV PORT=5000
ENV DEBUG=false

CMD ["python", "baidu_pan_player.py"]
```

### 构建和运行

```bash
# 构建镜像
docker build -t baidu-pan-player .

# 运行容器
docker run -d -p 5000:5000 --name baidu-pan-player baidu-pan-player

# 查看日志
docker logs -f baidu-pan-player
```

### Docker Compose

```yaml
version: '3.8'

services:
  baidu-pan-player:
    build: .
    ports:
      - "5000:5000"
    environment:
      - HOST=0.0.0.0
      - PORT=5000
      - DEBUG=false
    restart: unless-stopped
```

## 核心实现说明

### 1. crack_video接口

```python
def _get_crack_video_link(self, fs_id: str) -> Optional[str]:
    """
    使用crack_video接口获取视频播放地址
    这是百度网盘的视频破解接口，可以获取直接可播放的URL
    """
    # 使用streaming接口获取视频地址
    url = f"{self.D_PCS_URL}/rest/2.0/pcs/file"
    params = {
        'method': 'streaming',
        'path': path,
        'type': 'M3U8_AUTO_480',  # 视频质量
        'access_token': self._get_access_token(),
    }
    # ... 获取并返回播放地址
```

### 2. netdisk User-Agent

```python
def _success_response(self, play_url: str, file_info: Dict = None) -> Dict:
    """构建成功响应"""
    response = {
        'url': play_url,
        'header': {
            'User-Agent': 'netdisk',  # 关键：使用netdisk UA
            'Referer': 'https://pan.baidu.com',
        }
    }
    return response
```

### 3. 适配com.fongmi.android.tv

响应格式完全符合影视客户端的要求:
```python
{
    'parse': 0,      # 不需要解析
    'url': '...',    # 播放地址
    'header': {...}  # 必需的headers
}
```

## 注意事项

### 1. Cookie有效期

- 百度网盘Cookie (BDUSS/STOKEN) 通常30天有效
- 过期后需要重新获取
- 建议实现自动刷新机制（可参考Java版本的refresh_token逻辑）

### 2. API限流

- 百度网盘有API调用频率限制
- 普通用户: 约100次/小时
- VIP用户: 约500次/小时
- 建议实现请求缓存机制

### 3. 播放限速

- 非VIP用户可能被限速
- 大文件播放可能不稳定
- VIP用户体验更好

### 4. 安全性

- Cookie是敏感信息，注意保护
- 生产环境建议使用HTTPS
- 考虑添加认证机制
- 不要在公网直接暴露Cookie

## 扩展功能

### 1. 添加缓存

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def get_play_url_cached(cookie_hash, file_path):
    # 缓存播放地址
    pass
```

### 2. 添加认证

```python
from flask import request

def require_auth(f):
    def wrapper(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not verify_token(token):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return wrapper

@app.route('/play')
@require_auth
def play():
    # ...
```

### 3. 添加日志持久化

```python
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'baidu_pan_player.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
logger.addHandler(handler)
```

### 4. 添加监控

```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_latency = Histogram('request_latency_seconds', 'Request latency')

@app.before_request
def before_request():
    request_count.inc()
    # ...
```

## 故障排查

### 问题1: Cookie无效

**症状**: 返回401或获取文件列表失败

**解决**:
1. 检查Cookie格式是否正确
2. 重新获取Cookie
3. 确认BDUSS和STOKEN都存在

### 问题2: 无法获取播放地址

**症状**: 返回空URL或错误

**解决**:
1. 检查文件是否存在
2. 确认文件是视频格式
3. 尝试使用标准接口（set use_crack=False）
4. 检查网络连接

### 问题3: 播放卡顿

**症状**: 视频播放不流畅

**解决**:
1. 检查网络速度
2. 升级百度网盘VIP
3. 尝试使用代理
4. 降低视频质量

## 性能优化

### 1. 使用连接池

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

### 2. 异步处理

```python
import asyncio
import aiohttp

async def get_play_url_async(self, fs_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            return await response.json()
```

### 3. 添加Redis缓存

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_play_url_with_cache(fs_id):
    cache_key = f'play_url:{fs_id}'
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    result = get_play_url(fs_id)
    redis_client.setex(cache_key, 3600, json.dumps(result))  # 1小时
    return result
```

## 许可证

本项目遵循主项目的开源许可证。

## 贡献

欢迎提交Issue和Pull Request！

## 支持

如有问题，请查看:
1. [技术分析文档](../docs/BAIDU_PAN_ANALYSIS.md)
2. [配置指南](../docs/BAIDU_PAN_SETUP_GUIDE.md)
3. [流程图](../docs/BAIDU_PAN_FLOW.md)
