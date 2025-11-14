# 百度网盘播放地址提取流程图

## 1. 整体架构流程

```mermaid
graph TB
    A[用户/播放器] -->|HTTP请求| B[PlayController]
    B -->|验证token| C[SubscriptionService]
    C -->|解析参数| D[TvBoxService]
    D -->|获取文件信息| E[AListService]
    E -->|HTTP API调用| F[AList服务器]
    F -->|调用驱动| G[BaiduNetdisk/BaiduShare2]
    G -->|API请求| H[百度网盘服务器]
    H -->|返回播放地址| G
    G -->|FsDetail| F
    F -->|FsDetail JSON| E
    E -->|FsDetail对象| D
    D -->|构建响应| I[PlayUrl + Headers]
    I -->|JSON响应| A
    A -->|使用地址播放| J[视频流]
```

## 2. 详细请求流程

```mermaid
sequenceDiagram
    participant User as 播放器客户端
    participant PC as PlayController
    participant TVS as TvBoxService
    participant ALS as AListService
    participant ALIST as AList服务
    participant BAIDU as 百度网盘API

    User->>PC: GET /play/{token}?site=1&path=/video.mp4
    PC->>PC: 验证token
    PC->>TVS: getPlayUrl(site, path)
    
    TVS->>ALS: getFile(site, path)
    ALS->>ALIST: POST /api/fs/get
    Note over ALS,ALIST: {"path": "/video.mp4"}
    
    ALIST->>BAIDU: 调用crack_video API
    Note over ALIST,BAIDU: 使用cookie和refresh_token认证
    
    BAIDU-->>ALIST: 返回直接播放地址
    Note over BAIDU,ALIST: raw_url: https://d.pcs.baidu.com/...
    
    ALIST-->>ALS: FsDetail JSON
    Note over ALIST,ALS: {provider: "BaiduNetdisk", raw_url: "..."}
    
    ALS-->>TVS: FsDetail对象
    
    TVS->>TVS: 识别provider="Baidu"
    TVS->>TVS: 设置User-Agent="netdisk"
    
    TVS-->>PC: Map<String, Object>
    Note over TVS,PC: {url: "...", header: {User-Agent: "netdisk"}}
    
    PC-->>User: JSON响应
    
    User->>BAIDU: 使用返回的URL播放
    Note over User,BAIDU: Header: User-Agent: netdisk
    BAIDU-->>User: 视频流
```

## 3. 存储配置流程

```mermaid
graph LR
    A[添加百度网盘存储] --> B{存储类型}
    B -->|账户模式| C[BaiduNetdisk]
    B -->|分享模式| D[BaiduShare]
    
    C --> E[配置参数]
    E --> E1[cookie]
    E --> E2[refresh_token]
    E --> E3[client_id/secret]
    E --> E4[download_api=crack_video]
    E --> E5[custom_crack_ua=netdisk]
    
    D --> F[配置参数]
    F --> F1[surl分享ID]
    F --> F2[pwd提取码]
    F --> F3[root_folder_path]
    
    E4 -.->|关键配置| G[使用破解接口]
    E5 -.->|关键配置| H[模拟客户端]
    
    C --> I[AList存储池]
    D --> I
    I --> J[可供播放使用]
```

## 4. FsDetail数据流

```mermaid
graph TB
    A[AList API /api/fs/get] --> B[BaiduNetdisk驱动]
    B --> C{调用百度API}
    C -->|使用crack_video| D[获取视频播放地址]
    C -->|cookie认证| E[验证用户身份]
    
    D --> F[构建FsDetail对象]
    E --> F
    
    F --> G[name: 文件名]
    F --> H[size: 文件大小]
    F --> I[provider: BaiduNetdisk]
    F --> J[rawUrl: 播放地址]
    F --> K[sign: 签名]
    
    J -.->|核心数据| L[直接可播放的URL]
    I -.->|用于识别| M[设置特殊headers]
```

## 5. 代理判断流程

```mermaid
graph TB
    A[获取到rawUrl] --> B{检查URL类型}
    
    B -->|包含.strm| C[读取STRM文件内容]
    C --> D[302重定向到真实URL]
    
    B -->|包含.m3u8| E[302重定向]
    
    B -->|包含baidu.com| F{检查是否需要代理}
    F -->|用户配置useProxy| G[使用AList代理]
    F -->|直连模式| H[直接返回rawUrl]
    
    B -->|其他云盘| I{根据provider判断}
    I -->|需要代理| G
    I -->|可直连| H
    
    G --> J[buildAListProxyUrl]
    J --> K[/p/path?sign=xxx]
    
    H --> L[返回原始URL]
    
    K --> M[添加特殊headers]
    L --> M
    
    M --> N{provider类型}
    N -->|Baidu| O[User-Agent: netdisk]
    N -->|Quark| P[User-Agent: Quark UA + Cookie]
    N -->|Ali| Q[User-Agent: Ali UA + Referer]
    
    O --> R[最终播放配置]
    P --> R
    Q --> R
```

## 6. ProxyService处理流程

```mermaid
graph TB
    A[播放器请求代理] --> B[/p/token/site@id]
    B --> C[ProxyService.proxy]
    
    C --> D[解析参数获取PlayUrl]
    D --> E[从数据库获取path]
    E --> F[AListService.getFile]
    
    F --> G[获取FsDetail]
    G --> H{判断driver类型}
    
    H -->|BaiduNetdisk| I[需要代理]
    H -->|BaiduShare2| I
    H -->|其他proxyDrivers| I
    H -->|可直连| J[302重定向]
    
    I --> K[buildAListProxyUrl]
    K --> L[构建AList代理地址]
    L --> M[/p/path?sign=xxx]
    
    M --> N[设置headers]
    N --> O[User-Agent: netdisk]
    N --> P[Referer: 适当的referer]
    
    O --> Q[downloadStraight]
    P --> Q
    
    Q --> R[建立HTTP连接]
    R --> S[流式传输]
    S --> T[返回给播放器]
```

## 7. Token刷新机制

```mermaid
graph TB
    A[AList启动/定时任务] --> B[检查access_token]
    B --> C{是否即将过期}
    
    C -->|是| D[使用refresh_token]
    D --> E[调用百度刷新API]
    E --> F{刷新成功?}
    
    F -->|成功| G[更新access_token]
    G --> H[更新存储配置]
    H --> I[继续正常服务]
    
    F -->|失败| J[标记存储异常]
    J --> K[需要重新配置]
    
    C -->|否| I
    
    I --> L[用户请求播放]
    L --> M[使用有效token访问]
```

## 8. 错误处理流程

```mermaid
graph TB
    A[播放请求] --> B{Token验证}
    B -->|失败| C[返回401未授权]
    B -->|成功| D{获取文件信息}
    
    D -->|文件不存在| E[返回404]
    D -->|成功| F{获取播放地址}
    
    F -->|rawUrl为空| G[返回400错误]
    F -->|成功| H{网络请求}
    
    H -->|超时| I[返回504超时]
    H -->|连接失败| J[返回503服务不可用]
    H -->|成功| K[返回播放流]
    
    G --> L[日志记录]
    I --> L
    J --> L
    E --> L
    C --> L
    
    L --> M[错误分析]
    M --> N{可自动恢复?}
    N -->|是| O[重试机制]
    N -->|否| P[通知用户]
```

## 9. 数据模型关系

```mermaid
classDiagram
    class DriverAccount {
        +Integer id
        +DriverType type
        +String name
        +String cookie
        +String token
        +String folder
        +boolean useProxy
    }
    
    class Share {
        +Integer id
        +Integer type
        +String path
        +String shareId
        +String password
        +String folderId
    }
    
    class Storage {
        +int id
        +String driver
        +String path
        +String addition
        +boolean webProxy
    }
    
    class BaiduNetdisk {
        +BaiduNetdisk(DriverAccount)
        -String driver = "BaiduNetdisk"
        -String download_api = "crack_video"
        -String custom_crack_ua = "netdisk"
    }
    
    class BaiduShare {
        +BaiduShare(Share)
        -String driver = "BaiduShare2"
    }
    
    class FsDetail {
        +String name
        +String provider
        +String rawUrl
        +String sign
        +long size
    }
    
    class PlayUrl {
        +Integer id
        +Integer site
        +String path
        +Instant time
    }
    
    DriverAccount --> BaiduNetdisk : 创建
    Share --> BaiduShare : 创建
    BaiduNetdisk --|> Storage : 继承
    BaiduShare --|> Storage : 继承
    Storage --> FsDetail : AList返回
    FsDetail --> PlayUrl : 生成
```

## 10. 关键配置参数说明

```mermaid
mindmap
  root((百度网盘配置))
    认证参数
      cookie
        BDUSS
        STOKEN
      refresh_token
        自动刷新
      client_id
        应用标识
      client_secret
        应用密钥
    
    破解参数
      download_api
        crack_video核心
      custom_crack_ua
        netdisk模拟
      
    功能参数
      root_folder_path
        根目录
      concurrency
        并发数
      order_by
        排序字段
      only_list_video_file
        仅列出视频
        
    分享参数
      surl
        分享ID
      pwd
        提取码
```

## 流程总结

### 核心流程链路

1. **请求阶段**: 用户 → PlayController → TvBoxService
2. **获取阶段**: TvBoxService → AListService → AList → 百度网盘
3. **处理阶段**: 识别provider → 设置headers → 判断代理
4. **返回阶段**: 构建响应 → 返回URL和headers → 播放器播放

### 关键技术点

- **破解接口**: `download_api: "crack_video"`
- **UA伪装**: `User-Agent: "netdisk"`
- **自动刷新**: refresh_token机制
- **代理支持**: AList的/p接口
- **灵活配置**: 支持账户和分享两种模式
