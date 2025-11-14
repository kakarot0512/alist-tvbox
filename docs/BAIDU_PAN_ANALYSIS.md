# 百度网盘播放地址提取流程分析

## 概述

本文档详细分析了AList-TvBox项目中如何通过百度网盘连接提取可播放的地址链接的完整流程。

## 核心组件

### 1. 存储驱动配置

#### 1.1 BaiduNetdisk（百度网盘账户）

**文件位置**: `src/main/java/cn/har01d/alist_tvbox/storage/BaiduNetdisk.java`

```java
public class BaiduNetdisk extends Storage {
    public BaiduNetdisk(DriverAccount account) {
        super(account, "BaiduNetdisk");
        addAddition("cookie", account.getCookie());
        addAddition("refresh_token", account.getToken());
        addAddition("root_folder_path", account.getFolder());
        addAddition("concurrency", account.getConcurrency());
        addAddition("order_by", "name");
        addAddition("order_direction", "asc");
        
        // 关键配置：破解参数
        if (StringUtils.isBlank(account.getAddition())) {
            addAddition("client_id", "iYCeC9g08h5vuP9UqvPHKKSVrKFXGa1v");
            addAddition("client_secret", "jXiFMOPVPCWlO2M5CwWQzffpNPaGTRBG");
        } else {
            addAddition("client_id", "IlLqBbU3GjQ0t46TRwFateTprHWl39zF");
            addAddition("client_secret", "");
        }
        
        // 核心破解设置
        addAddition("custom_crack_ua", "netdisk");
        addAddition("download_api", "crack_video");  // 使用破解视频API
        addAddition("only_list_video_file", true);
        buildAddition(account);
    }
}
```

**关键配置说明**:
- `cookie`: 百度网盘登录凭证
- `refresh_token`: 刷新令牌，用于自动续期
- `download_api: "crack_video"`: **最关键配置**，使用百度网盘的破解视频接口
- `custom_crack_ua: "netdisk"`: 自定义UA，模拟官方客户端
- `client_id/client_secret`: 百度开放平台应用凭证

#### 1.2 BaiduShare（百度网盘分享）

**文件位置**: `src/main/java/cn/har01d/alist_tvbox/storage/BaiduShare.java`

```java
public class BaiduShare extends Storage {
    public BaiduShare(Share share) {
        super(share, "BaiduShare2");  // 使用AList的BaiduShare2驱动
        addAddition("surl", share.getShareId());  // 分享链接的surl参数
        addAddition("pwd", share.getPassword());  // 分享密码
        addAddition("root_folder_path", share.getFolderId());  // 根文件夹路径
        buildAddition();
    }
}
```

**配置说明**:
- `BaiduShare2`: AList的百度分享驱动（第二版）
- `surl`: 从分享链接提取的唯一标识符
- `pwd`: 分享密码（提取码）
- `root_folder_path`: 指定访问的文件夹路径

### 2. 播放地址提取流程

#### 2.1 请求入口

**文件位置**: `src/main/java/cn/har01d/alist_tvbox/web/PlayController.java`

```java
@GetMapping("/play/{token}")
public Object play(@PathVariable String token, Integer site, String path, 
                   String id, String bvid, String type, boolean dash, 
                   HttpServletRequest request) throws IOException {
    // 1. 验证访问令牌
    subscriptionService.checkToken(token);
    
    // 2. 解析请求参数，确定站点和路径
    if (StringUtils.isNotBlank(id)) {
        String[] parts = id.split("@");
        if (parts.length > 1) {
            site = Integer.parseInt(parts[0]);
            path = parts[1];
            try {
                path = proxyService.getPath(Integer.parseInt(path));
            } catch (NumberFormatException e) {
                log.debug("", e);
            }
        }
    }
    
    // 3. 调用TvBoxService获取播放地址
    Map<String, Object> result = tvBoxService.getPlayUrl(site, path, getSub, client);
    return result;
}
```

#### 2.2 获取文件详情

**文件位置**: `src/main/java/cn/har01d/alist_tvbox/service/AListService.java`

```java
public FsDetail getFile(Site site, String path) {
    int version = getVersion(site);
    if (version == 2) {
        return getFileV2(site, path);
    } else {
        return getFileV3(site, path);
    }
}

private FsDetail getFileV3(Site site, String path) {
    String url = getUrl(site) + "/api/fs/get";
    FsRequest request = new FsRequest();
    request.setPassword(site.getPassword());
    request.setPath(path);
    
    if (StringUtils.isNotBlank(site.getFolder())) {
        request.setPath(fixPath(site.getFolder() + "/" + path));
    }
    
    log.debug("call api: {} request: {}", url, request);
    // 调用AList的/api/fs/get接口
    FsDetailResponse response = post(site, url, request, FsDetailResponse.class);
    logError(response);
    log.debug("get file: {} {}", path, response.getData());
    return response.getData();
}
```

**FsDetail对象结构**:
```java
@Data
public class FsDetail {
    private String name;           // 文件名
    private int type;              // 类型：1=文件夹，2=文件
    private boolean isDir;         // 是否是目录
    private String modified;       // 修改时间
    private long size;             // 文件大小
    private String sign;           // 签名（用于验证）
    private String thumb;          // 缩略图
    private String provider;       // 存储提供商，如"BaiduNetdisk"、"BaiduShare2"
    private String rawUrl;         // **关键字段**: 原始播放地址
}
```

#### 2.3 构建播放URL

**文件位置**: `src/main/java/cn/har01d/alist_tvbox/service/TvBoxService.java`

```java
public Map<String, Object> getPlayUrl(Integer siteId, String path, 
                                     boolean getSub, String client) {
    Site site = siteService.getById(siteId);
    
    // 1. 获取文件详情
    FsDetail fsDetail = aListService.getFile(site, path);
    if (fsDetail == null) {
        throw new BadRequestException("找不到文件 " + path);
    }
    
    // 2. 获取原始URL并修复
    String url = fixHttp(fsDetail.getRawUrl());
    
    Map<String, Object> result = new HashMap<>();
    result.put("parse", 0);  // 不需要解析
    result.put("playUrl", "");
    
    // 3. 特殊处理：根据客户端和提供商判断是否需要代理
    if ("com.fongmi.android.tv".equals(client)) {
        // 影视客户端，直接使用原始URL
    } else if ((fsDetail.getProvider().contains("Aliyundrive") && 
                !fsDetail.getRawUrl().contains("115cdn.net")) ||
               (("open".equals(client) || "node".equals(client)) && 
                fsDetail.getProvider().contains("115"))) {
        // 阿里云盘或115需要使用代理
        url = buildProxyUrl(site, name, path);
    }
    
    result.put("url", url);
    
    // 4. 判断是否需要使用代理
    if (isUseProxy(url)) {
        url = buildProxyUrl(site, name, path);
        result.put("url", url);
    }
    
    // 5. 针对不同存储提供商设置特殊headers
    if (fsDetail.getProvider().contains("Baidu")) {
        // **百度网盘关键配置**
        result.put("header", Map.of("User-Agent", "netdisk"));
    } else if (fsDetail.getProvider().equals("QuarkShare") || 
               fsDetail.getProvider().equals("Quark")) {
        // 夸克网盘
        var account = getDriverAccount(url, DriverType.QUARK);
        String cookie = account.getCookie();
        result.put("header", Map.of(
            "Cookie", cookie, 
            "User-Agent", Constants.QUARK_USER_AGENT, 
            "Referer", "https://pan.quark.cn"
        ));
    } else if (url.contains("ali")) {
        // 阿里云盘
        result.put("format", "application/octet-stream");
        result.put("header", Map.of(
            "User-Agent", appProperties.getUserAgent(), 
            "Referer", Constants.ALIPAN, 
            "origin", Constants.ALIPAN
        ));
    }
    
    // 6. 获取字幕（如果需要）
    if (getSub) {
        List<Subtitle> subtitles = new ArrayList<>();
        Subtitle subtitle = getSubtitle(site, isMediaFile(path) ? getParent(path) : path, name);
        if (subtitle != null) {
            subtitles.add(subtitle);
        }
        if (!subtitles.isEmpty()) {
            result.put("subt", subtitles.get(0).getUrl());
        }
        result.put("subs", subtitles);
    }
    
    log.debug("[{}] getPlayUrl result: {}", fsDetail.getProvider(), result);
    return result;
}
```

### 3. 代理处理

#### 3.1 代理判断逻辑

**文件位置**: `src/main/java/cn/har01d/alist_tvbox/service/ProxyService.java`

```java
public class ProxyService {
    // 需要代理的驱动类型
    private final Set<String> proxyDrivers = Set.of(
        "AliyundriveOpen", 
        "AliyunShare", 
        "BaiduNetdisk",      // 百度网盘
        "BaiduShare2",       // 百度分享
        "Quark", 
        "UC", 
        "QuarkShare", 
        "UCShare", 
        "115 Cloud", 
        "115 Share"
    );
    
    public void proxy(String tid, HttpServletRequest request, 
                     HttpServletResponse response) throws IOException {
        String[] parts = tid.split("@");
        int id = Integer.parseInt(parts[1]);
        PlayUrl playUrl = playUrlRepository.findById(id)
            .orElseThrow(() -> new NotFoundException("Not found: " + id));
        String path = playUrl.getPath();
        String url;
        
        Map<String, String> headers = new HashMap<>();
        // 复制原始请求的headers
        var it = request.getHeaderNames().asIterator();
        while (it.hasNext()) {
            String name = it.next();
            headers.put(name, request.getHeader(name));
        }
        headers.put("user-agent", Constants.MOBILE_USER_AGENT);
        
        if (playUrl.getSite() == 0) {
            // 处理虎牙等直播流
            url = huyaParseService.getTrueUrl(playUrl.getPath());
            headers.put("user-agent", huyaParseService.getUa());
            headers.put("referer", "https://www.huya.com/");
        } else {
            Site site = siteService.getById(playUrl.getSite());
            FsDetail fsDetail = aListService.getFile(site, path);
            if (fsDetail == null) {
                throw new BadRequestException("找不到文件 " + path);
            }
            
            url = fsDetail.getRawUrl();
            String driver = fsDetail.getProvider();
            
            // 判断是否需要代理
            if (url.contains(".strm")) {
                // STRM文件，读取内容作为真实URL
                Request rq = new Request.Builder().url(url).get().build();
                try (Response rp = okHttpClient.newCall(rq).execute(); 
                     ResponseBody body = rp.body()) {
                    url = body != null ? body.string() : url;
                }
                response.sendRedirect(url);
                return;
            } else if (url.contains(".m3u8")) {
                // M3U8直接302重定向
                response.sendRedirect(url);
                return;
            } else if (proxyDrivers.contains(driver) || 
                       url.contains("115cdn") || 
                       url.contains("aliyundrive") ||
                       url.contains("baidu.com") ||    // 百度网盘URL
                       url.contains("quark.cn") || 
                       url.contains("uc.cn") ||
                       url.startsWith("http://localhost")) {
                // **需要通过AList代理**
                log.debug("{} {}", driver, url);
                url = buildAListProxyUrl(site, path, fsDetail.getSign());
            } else {
                // 302重定向到原始URL
                log.debug("302 {} {}", driver, url);
                response.sendRedirect(url);
                return;
            }
            
            log.debug("proxy url: {} {}", driver, url);
            headers.put("referer", Constants.ALIPAN);
        }
        
        log.trace("headers: {}", headers);
        
        // 通过代理下载
        downloadStraight(url, request, response, headers);
    }
    
    private String buildAListProxyUrl(Site site, String path, String sign) {
        if (site.getUrl().startsWith("http://localhost")) {
            // 使用本地AList服务
            return ServletUriComponentsBuilder.fromCurrentRequest()
                    .port(aListLocalService.getExternalPort())
                    .replacePath("/p" + path)
                    .replaceQuery(StringUtils.isBlank(sign) ? "" : "sign=" + sign)
                    .build()
                    .toUri()
                    .toASCIIString();
        } else {
            // 使用远程AList服务
            if (StringUtils.isNotBlank(site.getFolder())) {
                path = fixPath(site.getFolder() + "/" + path);
            }
            return UriComponentsBuilder.fromHttpUrl(site.getUrl())
                    .replacePath("/p" + path)
                    .replaceQuery(StringUtils.isBlank(sign) ? "" : "sign=" + sign)
                    .build()
                    .toUri()
                    .toASCIIString();
        }
    }
}
```

## 完整流程图

```
用户请求播放
    ↓
PlayController.play()
    ↓
验证token → subscriptionService.checkToken()
    ↓
解析路径参数
    ↓
TvBoxService.getPlayUrl(site, path)
    ↓
AListService.getFile(site, path)
    ↓
调用AList API: POST /api/fs/get
    {
        "path": "/我的百度网盘/视频.mp4",
        "password": ""
    }
    ↓
AList返回FsDetail对象
    {
        "name": "视频.mp4",
        "size": 1234567890,
        "provider": "BaiduNetdisk",  ← 识别为百度网盘
        "raw_url": "https://d.pcs.baidu.com/file/xxx?fid=xxx&..."  ← 播放地址
    }
    ↓
TvBoxService处理URL
    ├─ fixHttp(rawUrl) - 修复URL格式
    ├─ 判断provider.contains("Baidu")
    └─ 设置header: {"User-Agent": "netdisk"}  ← 关键：模拟百度客户端
    ↓
返回播放信息
    {
        "url": "https://d.pcs.baidu.com/file/xxx...",
        "header": {
            "User-Agent": "netdisk"
        },
        "parse": 0,
        "subs": [...]
    }
    ↓
播放器使用该URL和headers进行播放
```

## AList与百度网盘的交互

### AList的百度网盘驱动工作原理

1. **认证**：
   - 使用`refresh_token`自动刷新`access_token`
   - 使用`cookie`维持登录状态
   - 使用`client_id`和`client_secret`作为应用凭证

2. **文件列表**：
   - 调用百度网盘API获取文件列表
   - 支持按名称、时间等排序

3. **播放地址获取**（核心）：
   - **关键配置**: `download_api: "crack_video"`
   - 这个配置使AList使用百度网盘的**视频破解接口**
   - 该接口返回的URL是**直接可播放的地址**，不需要额外的权限验证
   - 配合`custom_crack_ua: "netdisk"`模拟官方客户端

4. **下载代理**：
   - AList提供`/p/<path>`代理接口
   - 自动处理百度网盘的权限验证
   - 转发视频流到客户端

### 百度网盘分享的处理

对于百度网盘分享链接（如：https://pan.baidu.com/s/1xxxxx），处理流程：

1. **解析分享链接**：
   ```
   https://pan.baidu.com/s/1xxxxx?pwd=abcd
   ↓
   surl: 1xxxxx
   pwd: abcd
   ```

2. **配置BaiduShare2存储**：
   ```java
   BaiduShare share = new BaiduShare(shareEntity);
   // 使用AList的BaiduShare2驱动
   // 自动处理分享验证和文件访问
   ```

3. **访问分享文件**：
   - AList自动验证提取码
   - 获取分享中的文件列表
   - 生成可播放地址

## 关键技术点

### 1. 破解视频接口

**download_api: "crack_video"** 是整个方案的核心：

- 这是百度网盘提供的特殊接口，用于获取视频的直接播放地址
- 区别于普通下载接口，视频接口返回的URL可以直接用于流媒体播放
- 需要配合特定的User-Agent（"netdisk"）使用
- 避免了频繁的权限验证和token刷新

### 2. User-Agent伪装

```java
result.put("header", Map.of("User-Agent", "netdisk"));
```

- 使用"netdisk"作为User-Agent
- 模拟百度网盘官方客户端
- 绕过部分限制和检测

### 3. 代理机制

两种代理方式：

1. **AList-TvBox代理**：
   ```
   https://your-domain/p/{token}/{site}@{id}
   ```
   - 通过AList-TvBox服务转发
   - 适用于需要额外处理的场景

2. **AList直接代理**：
   ```
   http://alist-server/p/{path}?sign={sign}
   ```
   - 直接通过AList服务代理
   - 性能更好，推荐用于百度网盘

### 4. 自动token刷新

AList的百度网盘驱动会：
- 定期检查`access_token`有效期
- 使用`refresh_token`自动刷新
- 无需手动维护

## 配置示例

### 添加百度网盘账户

通过API或管理界面：

```json
{
  "type": "BAIDU",
  "name": "我的百度网盘",
  "cookie": "BDUSS=xxx; STOKEN=xxx",
  "token": "refresh_token_value",
  "folder": "/",
  "concurrency": 3
}
```

### 添加百度网盘分享

```json
{
  "type": 10,
  "path": "我的百度分享/电影",
  "shareId": "1xxxxx",
  "password": "abcd",
  "folderId": "/"
}
```

或使用文本导入格式：
```
我的百度分享/电影  10:1xxxxx  root  abcd
```

## 常见问题

### Q1: 为什么需要cookie和refresh_token？

**答**: 
- `cookie`: 用于维持登录会话，包含BDUSS和STOKEN
- `refresh_token`: 用于自动刷新access_token，保持长期有效

### Q2: 如何获取client_id和client_secret？

**答**: 
- 代码中已提供默认值
- 也可以在百度开放平台注册应用获取自己的凭证
- 不同凭证可能有不同的限流策略

### Q3: 播放失败怎么办？

**答**: 检查以下几点：
1. cookie是否过期（重新登录获取）
2. refresh_token是否有效
3. 文件是否还存在
4. 网络是否正常
5. User-Agent是否正确设置为"netdisk"

### Q4: 是否支持4K视频？

**答**: 
- 支持，但取决于百度网盘账户类型
- 普通用户可能被限速
- VIP用户可获得更好的播放体验

### Q5: 分享链接失效怎么办？

**答**: 
- 检查分享是否已过期
- 验证提取码是否正确
- 尝试重新获取分享链接

## 总结

AList-TvBox通过以下方式实现百度网盘播放地址提取：

1. **配置层**: 使用BaiduNetdisk/BaiduShare驱动配置存储
2. **API层**: 通过AList的API获取文件信息和播放地址
3. **破解层**: 使用"crack_video" API获取直接播放地址
4. **伪装层**: 使用"netdisk" User-Agent模拟官方客户端
5. **代理层**: 通过AList代理处理复杂的权限验证

整个流程完全自动化，用户只需配置cookie和refresh_token，即可实现：
- 自动刷新token
- 自动获取播放地址
- 自动处理分享链接
- 流畅的视频播放体验

**核心优势**：
- ✅ 无需手动解析复杂的百度网盘API
- ✅ 自动维护登录状态
- ✅ 支持账户和分享两种模式
- ✅ 直接获取可播放地址，无需二次解析
- ✅ 完整的错误处理和日志记录
