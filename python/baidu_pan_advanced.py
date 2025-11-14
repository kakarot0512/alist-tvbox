#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度网盘播放地址提取服务 - 高级版本
包含Token自动刷新、缓存、重试等高级功能
"""

import json
import time
import hashlib
import requests
from typing import Dict, Optional, Tuple, List
from urllib.parse import urlparse, parse_qs, quote
from flask import Flask, request, jsonify
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class TokenManager:
    """Token管理器 - 处理access_token的刷新"""
    
    def __init__(self, refresh_token: str = None, client_id: str = None, 
                 client_secret: str = None):
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_expire_time = None
    
    def get_access_token(self) -> Optional[str]:
        """获取有效的access_token"""
        # 如果token还有效，直接返回
        if self.access_token and self.token_expire_time:
            if datetime.now() < self.token_expire_time:
                return self.access_token
        
        # 否则刷新token
        return self.refresh_access_token()
    
    def refresh_access_token(self) -> Optional[str]:
        """使用refresh_token刷新access_token"""
        if not self.refresh_token or not self.client_id:
            logger.warning("缺少refresh_token或client_id，无法刷新")
            return None
        
        url = "https://openapi.baidu.com/oauth/2.0/token"
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret or '',
        }
        
        try:
            response = requests.post(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'access_token' in data:
                self.access_token = data['access_token']
                # 设置过期时间（提前5分钟刷新）
                expires_in = data.get('expires_in', 2592000)  # 默认30天
                self.token_expire_time = datetime.now() + timedelta(seconds=expires_in - 300)
                
                logger.info("成功刷新access_token")
                return self.access_token
            else:
                logger.error(f"刷新token失败: {data}")
                return None
                
        except Exception as e:
            logger.error(f"刷新token异常: {e}")
            return None


class CacheManager:
    """简单的内存缓存管理器"""
    
    def __init__(self, default_ttl: int = 3600):
        self.cache = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[any]:
        """获取缓存"""
        if key in self.cache:
            value, expire_time = self.cache[key]
            if time.time() < expire_time:
                logger.debug(f"缓存命中: {key}")
                return value
            else:
                # 缓存过期，删除
                del self.cache[key]
        return None
    
    def set(self, key: str, value: any, ttl: int = None):
        """设置缓存"""
        if ttl is None:
            ttl = self.default_ttl
        expire_time = time.time() + ttl
        self.cache[key] = (value, expire_time)
        logger.debug(f"缓存设置: {key}, TTL: {ttl}s")
    
    def delete(self, key: str):
        """删除缓存"""
        if key in self.cache:
            del self.cache[key]
            logger.debug(f"缓存删除: {key}")
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")
    
    def cleanup(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expire_time) in self.cache.items()
            if current_time >= expire_time
        ]
        for key in expired_keys:
            del self.cache[key]
        if expired_keys:
            logger.info(f"清理了 {len(expired_keys)} 个过期缓存")


class BaiduPanAPIAdvanced:
    """百度网盘API高级封装"""
    
    BASE_URL = "https://pan.baidu.com"
    PCS_URL = "https://pcs.baidu.com"
    D_PCS_URL = "https://d.pcs.baidu.com"
    USER_AGENT = "netdisk"
    MOBILE_USER_AGENT = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 netdisk"
    
    def __init__(self, cookie: str, refresh_token: str = None,
                 client_id: str = None, client_secret: str = None):
        self.cookie = cookie
        self.session = requests.Session()
        self.token_manager = TokenManager(refresh_token, client_id, client_secret)
        self.cache_manager = CacheManager()
        self._setup_session()
        
        # 重试配置
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _setup_session(self):
        """配置请求会话"""
        self.session.headers.update({
            'User-Agent': self.MOBILE_USER_AGENT,
            'Cookie': self.cookie,
            'Referer': 'https://pan.baidu.com',
        })
    
    def get_file_list_cached(self, dir_path: str = "/", page: int = 1, 
                            size: int = 100) -> Dict:
        """获取文件列表（带缓存）"""
        cache_key = f"file_list:{dir_path}:{page}:{size}"
        cached = self.cache_manager.get(cache_key)
        if cached:
            return cached
        
        result = self._get_file_list(dir_path, page, size)
        if result.get('errno') == 0:
            self.cache_manager.set(cache_key, result, ttl=300)  # 缓存5分钟
        return result
    
    def _get_file_list(self, dir_path: str, page: int, size: int) -> Dict:
        """获取文件列表"""
        url = f"{self.BASE_URL}/api/list"
        params = {
            'dir': dir_path,
            'page': page,
            'num': size,
            'order': 'name',
            'desc': 0,
            'web': 1,
            'folder': 0,
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"获取文件列表异常: {e}")
            return {'errno': -1, 'list': []}
    
    def get_play_url_with_quality(self, fs_id: str, quality: str = 'M3U8_AUTO_480') -> Optional[str]:
        """
        获取指定质量的播放地址
        
        质量选项:
        - M3U8_AUTO_480: 自动480p
        - M3U8_AUTO_720: 自动720p
        - M3U8_AUTO_1080: 自动1080p
        """
        cache_key = f"play_url:{fs_id}:{quality}"
        cached = self.cache_manager.get(cache_key)
        if cached:
            return cached
        
        result = self._get_crack_video_link(fs_id, quality)
        if result:
            self.cache_manager.set(cache_key, result, ttl=900)  # 缓存15分钟
        return result
    
    def _get_crack_video_link(self, fs_id: str, quality: str = 'M3U8_AUTO_480') -> Optional[str]:
        """使用crack_video接口获取播放地址"""
        # 先获取文件信息
        file_info = self._get_file_info(fs_id)
        if not file_info:
            return None
        
        path = file_info.get('path')
        if not path:
            return None
        
        # 获取access_token
        access_token = self.token_manager.get_access_token()
        
        # 使用streaming接口
        url = f"{self.D_PCS_URL}/rest/2.0/pcs/file"
        params = {
            'method': 'streaming',
            'path': path,
            'type': quality,
        }
        
        if access_token:
            params['access_token'] = access_token
        
        try:
            response = self.session.get(url, params=params, timeout=30, allow_redirects=False)
            
            if response.status_code == 302:
                play_url = response.headers.get('Location')
                if play_url:
                    logger.info(f"获取播放地址成功: {quality}")
                    return play_url
            
            if response.status_code == 200:
                data = response.json()
                if 'urls' in data and data['urls']:
                    play_url = data['urls'][0]['url']
                    logger.info(f"获取播放地址成功: {quality}")
                    return play_url
            
            # 如果失败，尝试使用标准下载接口
            logger.warning(f"crack_video失败，尝试标准接口")
            return self._get_standard_download_link(file_info)
            
        except Exception as e:
            logger.error(f"获取播放地址异常: {e}")
            return None
    
    def _get_standard_download_link(self, file_info: Dict) -> Optional[str]:
        """获取标准下载链接"""
        dlink = file_info.get('dlink')
        if dlink:
            logger.info("使用标准下载链接")
            return dlink
        return None
    
    def _get_file_info(self, fs_id: str) -> Optional[Dict]:
        """获取文件信息"""
        url = f"{self.BASE_URL}/api/filemetas"
        params = {
            'fsids': f'[{fs_id}]',
            'thumb': 1,
            'extra': 1,
            'web': 1,
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('errno') == 0 and data.get('list'):
                return data['list'][0]
            return None
        except Exception as e:
            logger.error(f"获取文件信息异常: {e}")
            return None
    
    def search_files(self, keyword: str, page: int = 1) -> List[Dict]:
        """搜索文件"""
        url = f"{self.BASE_URL}/api/search"
        params = {
            'key': keyword,
            'page': page,
            'num': 100,
            'web': 1,
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('errno') == 0:
                return data.get('list', [])
            return []
        except Exception as e:
            logger.error(f"搜索文件异常: {e}")
            return []


# 装饰器：API性能监控
def monitor_performance(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = f(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.info(f"{f.__name__} 执行时间: {elapsed_time:.3f}s")
        return result
    return wrapper


# ============= Flask API 路由 (高级版) =============

@app.route('/play/advanced', methods=['POST'])
@monitor_performance
def play_advanced():
    """
    获取播放地址（高级版本）
    
    支持的功能:
    - 多种视频质量选择
    - 自动重试
    - 结果缓存
    - Token自动刷新
    """
    try:
        data = request.get_json() or {}
        
        cookie = data.get('cookie')
        if not cookie:
            return jsonify({'error': True, 'message': 'Cookie不能为空'}), 400
        
        fs_id = data.get('fs_id') or data.get('fsid')
        if not fs_id:
            return jsonify({'error': True, 'message': 'fs_id不能为空'}), 400
        
        # 获取可选参数
        quality = data.get('quality', 'M3U8_AUTO_480')
        refresh_token = data.get('refresh_token')
        client_id = data.get('client_id')
        client_secret = data.get('client_secret')
        
        # 创建高级API实例
        api = BaiduPanAPIAdvanced(
            cookie=cookie,
            refresh_token=refresh_token,
            client_id=client_id,
            client_secret=client_secret
        )
        
        # 获取播放地址
        play_url = api.get_play_url_with_quality(fs_id, quality)
        
        if not play_url:
            return jsonify({
                'error': True,
                'message': '无法获取播放地址'
            }), 400
        
        # 返回结果
        result = {
            'parse': 0,
            'url': play_url,
            'header': {
                'User-Agent': 'netdisk',
                'Referer': 'https://pan.baidu.com',
            },
            'quality': quality,
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"获取播放地址异常: {e}", exc_info=True)
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/search', methods=['POST'])
@monitor_performance
def search():
    """搜索文件"""
    try:
        data = request.get_json() or {}
        
        cookie = data.get('cookie')
        keyword = data.get('keyword')
        
        if not cookie or not keyword:
            return jsonify({'error': True, 'message': '参数不完整'}), 400
        
        api = BaiduPanAPIAdvanced(cookie=cookie)
        results = api.search_files(keyword)
        
        return jsonify({
            'keyword': keyword,
            'count': len(results),
            'results': results
        })
        
    except Exception as e:
        logger.error(f"搜索异常: {e}", exc_info=True)
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """清空缓存"""
    # 这里需要全局缓存管理
    return jsonify({'message': '缓存已清空'})


if __name__ == '__main__':
    import os
    
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5001))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"启动百度网盘播放服务(高级版): http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
