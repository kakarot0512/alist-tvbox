# 使用示例

## 快速开始

### 1. 启动服务

```bash
cd python
python baidu_pan_player.py
```

服务将运行在 `http://localhost:5000`

### 2. 测试服务

```bash
# 健康检查
curl http://localhost:5000/health

# 查看API信息
curl http://localhost:5000/info
```

## 完整使用示例

### 示例1: 获取自己网盘中的视频播放地址

#### 步骤1: 获取Cookie

1. 打开百度网盘: https://pan.baidu.com
2. 登录账号
3. 按F12打开开发者工具
4. 刷新页面
5. 在Network标签中找到任意请求
6. 复制Cookie中的BDUSS和STOKEN

```
Cookie示例:
BDUSS=abc123...; STOKEN=xyz789...
```

#### 步骤2: 列出文件

```bash
curl -X POST http://localhost:5000/list \
  -H "Content-Type: application/json" \
  -d '{
    "cookie": "BDUSS=abc123; STOKEN=xyz789",
    "dir": "/视频"
  }'
```

响应示例:
```json
{
  "errno": 0,
  "list": [
    {
      "server_filename": "电影.mp4",
      "fs_id": 123456789,
      "size": 1234567890,
      "isdir": 0
    }
  ]
}
```

#### 步骤3: 获取播放地址

使用上一步获取的`fs_id`:

```bash
curl -X POST http://localhost:5000/play \
  -H "Content-Type: application/json" \
  -d '{
    "cookie": "BDUSS=abc123; STOKEN=xyz789",
    "fs_id": "123456789"
  }'
```

响应示例:
```json
{
  "parse": 0,
  "url": "https://d.pcs.baidu.com/file/xxx...",
  "header": {
    "User-Agent": "netdisk",
    "Referer": "https://pan.baidu.com"
  },
  "name": "电影.mp4",
  "size": 1234567890
}
```

#### 步骤4: 在播放器中使用

使用返回的URL和headers播放视频:

```python
import requests

# 从API获取播放信息
play_info = {
    "url": "https://d.pcs.baidu.com/file/xxx...",
    "header": {
        "User-Agent": "netdisk",
        "Referer": "https://pan.baidu.com"
    }
}

# 下载视频
response = requests.get(
    play_info['url'],
    headers=play_info['header'],
    stream=True
)

# 保存或播放
with open('video.mp4', 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

### 示例2: 使用Python测试客户端

```bash
# 健康检查
python test_client.py health

# 列出文件
python test_client.py list "BDUSS=abc123; STOKEN=xyz789" "/视频"

# 获取播放地址（通过路径）
python test_client.py play "BDUSS=abc123; STOKEN=xyz789" path "/视频/电影.mp4"

# 获取播放地址（通过fs_id）
python test_client.py play "BDUSS=abc123; STOKEN=xyz789" fsid "123456789"
```

### 示例3: 在com.fongmi.android.tv客户端中集成

#### 方案A: 作为播放解析接口

在影视客户端的配置中添加:

```json
{
  "sites": [
    {
      "key": "baidu_pan",
      "name": "百度网盘",
      "type": 3,
      "api": "http://your-server:5000/play",
      "searchable": 0,
      "quickSearch": 0
    }
  ]
}
```

#### 方案B: 自定义解析

```javascript
// 在客户端中调用
function getBaiduPlayUrl(fsId, cookie) {
    const url = 'http://your-server:5000/play';
    const data = {
        cookie: cookie,
        fs_id: fsId
    };
    
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (!result.error) {
            // 返回播放配置
            return {
                url: result.url,
                headers: result.header
            };
        }
        throw new Error(result.message);
    });
}

// 使用示例
getBaiduPlayUrl('123456789', 'BDUSS=xxx; STOKEN=xxx')
    .then(config => {
        // 使用config.url和config.headers播放视频
        player.play(config.url, config.headers);
    });
```

### 示例4: cURL完整示例

#### GET请求示例

```bash
curl -G http://localhost:5000/play \
  --data-urlencode "cookie=BDUSS=abc123; STOKEN=xyz789" \
  --data-urlencode "file_path=/视频/电影.mp4"
```

#### POST请求示例

```bash
curl -X POST http://localhost:5000/play \
  -H "Content-Type: application/json" \
  -d @- << EOF
{
  "cookie": "BDUSS=abc123; STOKEN=xyz789",
  "file_path": "/视频/电影.mp4"
}
EOF
```

### 示例5: Python requests库

```python
import requests

def get_baidu_play_url(cookie, fs_id=None, file_path=None):
    """获取百度网盘播放地址"""
    url = "http://localhost:5000/play"
    
    data = {
        "cookie": cookie
    }
    
    if fs_id:
        data["fs_id"] = fs_id
    elif file_path:
        data["file_path"] = file_path
    else:
        raise ValueError("必须提供fs_id或file_path")
    
    response = requests.post(url, json=data)
    response.raise_for_status()
    
    result = response.json()
    if result.get('error'):
        raise Exception(result.get('message'))
    
    return result

# 使用示例1: 通过fs_id
play_info = get_baidu_play_url(
    cookie="BDUSS=abc123; STOKEN=xyz789",
    fs_id="123456789"
)

print(f"播放地址: {play_info['url']}")
print(f"Headers: {play_info['header']}")

# 使用示例2: 通过文件路径
play_info = get_baidu_play_url(
    cookie="BDUSS=abc123; STOKEN=xyz789",
    file_path="/视频/电影.mp4"
)
```

### 示例6: JavaScript/Node.js

```javascript
const axios = require('axios');

async function getBaiduPlayUrl(cookie, fsId) {
    try {
        const response = await axios.post('http://localhost:5000/play', {
            cookie: cookie,
            fs_id: fsId
        });
        
        if (response.data.error) {
            throw new Error(response.data.message);
        }
        
        return response.data;
    } catch (error) {
        console.error('获取播放地址失败:', error);
        throw error;
    }
}

// 使用示例
(async () => {
    const playInfo = await getBaiduPlayUrl(
        'BDUSS=abc123; STOKEN=xyz789',
        '123456789'
    );
    
    console.log('播放地址:', playInfo.url);
    console.log('Headers:', playInfo.header);
})();
```

### 示例7: 使用高级API（带Token刷新）

```bash
curl -X POST http://localhost:5001/play/advanced \
  -H "Content-Type: application/json" \
  -d '{
    "cookie": "BDUSS=abc123; STOKEN=xyz789",
    "fs_id": "123456789",
    "quality": "M3U8_AUTO_720",
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret"
  }'
```

质量选项:
- `M3U8_AUTO_480`: 480p (默认)
- `M3U8_AUTO_720`: 720p
- `M3U8_AUTO_1080`: 1080p

### 示例8: 批量获取播放地址

```python
import requests
import json

def batch_get_play_urls(cookie, fs_ids):
    """批量获取播放地址"""
    results = []
    
    for fs_id in fs_ids:
        try:
            response = requests.post(
                "http://localhost:5000/play",
                json={
                    "cookie": cookie,
                    "fs_id": str(fs_id)
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get('error'):
                    results.append({
                        'fs_id': fs_id,
                        'url': data['url'],
                        'name': data.get('name', ''),
                        'size': data.get('size', 0)
                    })
        except Exception as e:
            print(f"获取 {fs_id} 失败: {e}")
    
    return results

# 使用示例
cookie = "BDUSS=abc123; STOKEN=xyz789"
fs_ids = ["123456789", "987654321", "111222333"]

results = batch_get_play_urls(cookie, fs_ids)

print(f"成功获取 {len(results)} 个播放地址:")
for item in results:
    print(f"- {item['name']}: {item['url'][:50]}...")
```

### 示例9: 集成到Web应用

```html
<!DOCTYPE html>
<html>
<head>
    <title>百度网盘播放器</title>
</head>
<body>
    <h1>百度网盘视频播放</h1>
    
    <div>
        <input type="text" id="cookie" placeholder="输入Cookie" style="width: 400px;">
        <input type="text" id="fsId" placeholder="输入fs_id">
        <button onclick="getPlayUrl()">获取播放地址</button>
    </div>
    
    <div id="result"></div>
    
    <video id="player" controls style="width: 100%; max-width: 800px; margin-top: 20px;"></video>
    
    <script>
        async function getPlayUrl() {
            const cookie = document.getElementById('cookie').value;
            const fsId = document.getElementById('fsId').value;
            
            if (!cookie || !fsId) {
                alert('请输入Cookie和fs_id');
                return;
            }
            
            try {
                const response = await fetch('http://localhost:5000/play', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        cookie: cookie,
                        fs_id: fsId
                    })
                });
                
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('result').innerHTML = 
                        '<p style="color: red;">错误: ' + data.message + '</p>';
                    return;
                }
                
                // 显示结果
                document.getElementById('result').innerHTML = `
                    <p><strong>文件名:</strong> ${data.name}</p>
                    <p><strong>大小:</strong> ${formatSize(data.size)}</p>
                    <p><strong>播放地址:</strong> ${data.url.substring(0, 80)}...</p>
                `;
                
                // 设置视频源（注意：由于CORS限制，可能无法直接播放）
                document.getElementById('player').src = data.url;
                
            } catch (error) {
                document.getElementById('result').innerHTML = 
                    '<p style="color: red;">请求失败: ' + error.message + '</p>';
            }
        }
        
        function formatSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            let size = bytes;
            let unitIndex = 0;
            
            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }
            
            return size.toFixed(2) + ' ' + units[unitIndex];
        }
    </script>
</body>
</html>
```

### 示例10: Docker部署后使用

```bash
# 构建镜像
docker build -t baidu-pan-player .

# 运行容器
docker run -d \
  -p 5000:5000 \
  --name baidu-pan-player \
  --restart unless-stopped \
  baidu-pan-player

# 测试
curl http://localhost:5000/health

# 查看日志
docker logs -f baidu-pan-player

# 停止和删除
docker stop baidu-pan-player
docker rm baidu-pan-player
```

## 常见问题示例

### 问题1: Cookie过期

```python
# 检测Cookie是否有效
def check_cookie_valid(cookie):
    response = requests.post(
        "http://localhost:5000/list",
        json={
            "cookie": cookie,
            "dir": "/"
        }
    )
    
    data = response.json()
    return data.get('errno') == 0

# 使用
cookie = "BDUSS=abc123; STOKEN=xyz789"
if not check_cookie_valid(cookie):
    print("Cookie已过期，请重新获取")
```

### 问题2: 处理大文件

```python
import requests

def download_large_file(play_url, headers, output_file):
    """分块下载大文件"""
    response = requests.get(
        play_url,
        headers=headers,
        stream=True
    )
    
    total_size = int(response.headers.get('content-length', 0))
    downloaded = 0
    
    with open(output_file, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                progress = (downloaded / total_size) * 100
                print(f"\r下载进度: {progress:.2f}%", end='')
    
    print("\n下载完成!")

# 使用示例
play_info = get_baidu_play_url(cookie, fs_id)
download_large_file(
    play_info['url'],
    play_info['header'],
    'movie.mp4'
)
```

### 问题3: 错误重试

```python
import time

def get_play_url_with_retry(cookie, fs_id, max_retries=3):
    """带重试的获取播放地址"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://localhost:5000/play",
                json={
                    "cookie": cookie,
                    "fs_id": fs_id
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get('error'):
                    return data
            
            # 如果失败，等待后重试
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"重试 {attempt + 1}/{max_retries}，等待 {wait_time}秒...")
                time.sleep(wait_time)
        
        except Exception as e:
            print(f"请求失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    raise Exception("获取播放地址失败，已达最大重试次数")

# 使用
try:
    play_info = get_play_url_with_retry(cookie, fs_id)
    print("成功:", play_info['url'])
except Exception as e:
    print("失败:", e)
```

## 性能优化示例

### 使用连接池

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 创建会话with连接池
session = requests.Session()
retry = Retry(total=3, backoff_factor=0.3)
adapter = HTTPAdapter(
    max_retries=retry,
    pool_connections=10,
    pool_maxsize=10
)
session.mount('http://', adapter)
session.mount('https://', adapter)

# 使用会话
def get_play_url_optimized(cookie, fs_id):
    response = session.post(
        "http://localhost:5000/play",
        json={"cookie": cookie, "fs_id": fs_id}
    )
    return response.json()
```

## 总结

以上示例涵盖了:
- ✅ 基本使用方法
- ✅ 多种编程语言集成
- ✅ Web应用集成
- ✅ 移动客户端集成
- ✅ 错误处理和重试
- ✅ 性能优化
- ✅ 生产环境部署

选择适合你的场景的示例开始使用！
