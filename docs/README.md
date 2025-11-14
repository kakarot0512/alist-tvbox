# 百度网盘集成文档

本目录包含AList-TvBox项目中百度网盘功能的详细技术文档。

## 📚 文档目录

### 1. [百度网盘播放地址提取流程分析](./BAIDU_PAN_ANALYSIS.md)

**适合人群**: 开发者、技术研究人员

**内容概要**:
- 详细的代码分析和技术实现
- 核心组件和类的说明
- 完整的播放地址提取流程
- AList与百度网盘的交互机制
- 关键技术点解析

**主要章节**:
- 存储驱动配置（BaiduNetdisk、BaiduShare）
- 播放地址提取流程（请求入口 → 获取详情 → 构建URL）
- 代理处理机制
- 破解接口原理
- 常见问题和解决方案

---

### 2. [百度网盘流程图](./BAIDU_PAN_FLOW.md)

**适合人群**: 架构师、开发者、技术文档阅读者

**内容概要**:
- 使用Mermaid绘制的专业流程图
- 可视化的架构和数据流
- 序列图、类图、流程图等多种图表
- 清晰的组件交互关系

**包含图表**:
1. 整体架构流程图
2. 详细请求序列图
3. 存储配置流程
4. FsDetail数据流
5. 代理判断流程
6. ProxyService处理流程
7. Token刷新机制
8. 错误处理流程
9. 数据模型关系图
10. 关键配置参数思维导图

---

### 3. [百度网盘配置指南](./BAIDU_PAN_SETUP_GUIDE.md)

**适合人群**: 运维人员、普通用户、初学者

**内容概要**:
- 从零开始的配置教程
- 详细的参数获取方法
- 多种配置方式说明
- 测试验证步骤
- 常见问题解决方案

**主要章节**:
1. **前置准备**: 环境要求和所需信息
2. **获取参数**: 如何获取cookie、refresh_token等
3. **配置账户**: 三种配置方式（Web界面、API、配置文件）
4. **配置分享**: 单个配置和批量导入
5. **测试验证**: 完整的测试流程
6. **常见问题**: 20+个常见问题及解决方案
7. **高级配置**: 自定义配置和优化技巧
8. **最佳实践**: 安全建议、性能优化、目录组织
9. **故障排查**: 系统化的排查流程

---

## 🚀 快速开始

### 对于用户
如果你是第一次使用百度网盘功能，建议按以下顺序阅读：

1. 📖 **先读**: [配置指南](./BAIDU_PAN_SETUP_GUIDE.md) - 了解如何配置
2. 🔧 **实践**: 按照指南完成配置
3. ❓ **遇到问题**: 查看配置指南中的"常见问题"章节

### 对于开发者
如果你想了解技术实现细节，建议按以下顺序阅读：

1. 📊 **先看**: [流程图](./BAIDU_PAN_FLOW.md) - 快速了解整体架构
2. 📚 **深入**: [技术分析](./BAIDU_PAN_ANALYSIS.md) - 理解代码实现
3. 🔧 **实践**: [配置指南](./BAIDU_PAN_SETUP_GUIDE.md) - 验证理解

---

## 🎯 核心功能

### 支持的功能

✅ **百度网盘账户集成**
- 自动登录和token刷新
- 文件列表浏览
- 视频直接播放
- 字幕自动匹配

✅ **百度网盘分享**
- 分享链接解析
- 提取码验证
- 批量导入分享
- 分享文件播放

✅ **高级特性**
- 破解视频接口获取直链
- User-Agent伪装
- 智能代理选择
- 并发控制
- 缓存优化

---

## 🔑 关键技术点

### 1. 破解视频接口

```java
addAddition("download_api", "crack_video");
addAddition("custom_crack_ua", "netdisk");
```

这是整个方案的核心，使用百度网盘的视频破解接口获取直接可播放的URL。

### 2. 自动Token刷新

```java
addAddition("refresh_token", account.getToken());
```

配置refresh_token后，AList会自动刷新access_token，无需手动维护。

### 3. User-Agent伪装

```java
result.put("header", Map.of("User-Agent", "netdisk"));
```

模拟百度网盘官方客户端，绕过部分限制。

### 4. 智能代理

根据不同情况自动选择是否使用代理：
- 直连模式：性能最好
- AList代理：兼容性最好

---

## 📊 技术架构

```
用户/播放器
    ↓
PlayController (请求入口)
    ↓
TvBoxService (业务逻辑)
    ↓
AListService (AList交互)
    ↓
AList Server (存储管理)
    ↓
BaiduNetdisk Driver (百度网盘驱动)
    ↓
百度网盘API (获取播放地址)
```

详细的流程图请查看 [流程图文档](./BAIDU_PAN_FLOW.md)。

---

## 🔧 配置示例

### 最小化配置

```json
{
  "type": "BAIDU",
  "name": "我的百度网盘",
  "cookie": "BDUSS=xxx; STOKEN=xxx"
}
```

### 完整配置

```json
{
  "type": "BAIDU",
  "name": "我的百度网盘",
  "cookie": "BDUSS=xxx; STOKEN=xxx",
  "token": "refresh_token_value",
  "folder": "/",
  "concurrency": 3,
  "useProxy": false,
  "addition": "{\"client_id\":\"...\",\"client_secret\":\"...\"}"
}
```

详细的配置说明请查看 [配置指南](./BAIDU_PAN_SETUP_GUIDE.md)。

---

## ❓ 常见问题

### Q: 配置后看不到文件？
**A**: 检查cookie是否有效，可能需要重新获取。详见[配置指南 - Q1](./BAIDU_PAN_SETUP_GUIDE.md#q1-配置后看不到文件)

### Q: 播放卡顿或失败？
**A**: 尝试启用代理模式，或升级百度网盘VIP。详见[配置指南 - Q2](./BAIDU_PAN_SETUP_GUIDE.md#q2-播放失败或卡顿)

### Q: Token频繁过期？
**A**: 配置refresh_token实现自动刷新。详见[配置指南 - Q4](./BAIDU_PAN_SETUP_GUIDE.md#q4-token过期问题)

更多问题请查看 [配置指南 - 常见问题](./BAIDU_PAN_SETUP_GUIDE.md#常见问题) 章节。

---

## 📖 相关资源

### 官方文档
- [AList官方文档](https://alist.nn.ci/)
- [AList-TvBox主文档](../README.md)

### 百度网盘相关
- [百度网盘开放平台](https://openapi.baidu.com/)
- [百度网盘Web版](https://pan.baidu.com/)

### 开发资源
- [项目源码](../)
- [Issues](../../issues)
- [Pull Requests](../../pulls)

---

## 🤝 贡献

欢迎贡献文档改进：

1. Fork本项目
2. 创建你的特性分支
3. 提交你的改动
4. 推送到分支
5. 创建Pull Request

文档贡献指南：
- 保持清晰简洁的写作风格
- 提供实际的代码示例
- 添加截图或流程图
- 更新目录和索引

---

## 📝 更新日志

### 2024-11-14
- ✨ 新增完整的百度网盘技术分析文档
- 📊 添加详细的流程图和架构图
- 📚 完善配置指南和最佳实践
- 🐛 修正文档中的错误和遗漏

---

## 📄 许可证

本文档遵循项目的开源许可证。

---

## 💬 反馈

如果你有任何问题、建议或反馈：

- 📧 提交Issue
- 💬 参与讨论
- 🌟 Star本项目
- 🔄 Fork并改进

感谢你的关注和支持！🎉
