#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度网盘播放地址提取服务
直接调用百度网盘crack_video API获取可播放地址
专为com.fongmi.android.tv影视客户端优化
"""

import json
import time
import hashlib
import requests
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs, quote
from flask import Flask, request, jsonify, Response
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class BaiduPanAPI:
    """百度网盘API封装"""
    
    # API端点
    BASE_URL = "https://pan.baidu.com"
    PCS_URL = "https://pcs.baidu.com"
    D_PCS_URL = "https://d.pcs.baidu.com"
    
    # User-Agent - 模拟百度网盘客户端
    USER_AGENT = "netdisk"
    MOBILE_USER_AGENT = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 netdisk"
    
    # 客户端凭证（从分析中获取的默认值）
    CLIENT_ID = "iYCeC9g08h5vuP9UqvPHKKSVrKFXGa1v"
    CLIENT_SECRET = "jXiFMOPVPCWlO2M5CwWQzffpNPaGTRBG"
    
    def __init__(self, cookie: str, client_id: str = None, client_secret: str = None):
        """
        初始化百度网盘API
        
        Args:
            cookie: 百度网盘Cookie (BDUSS和STOKEN)
            client_id: 可选的自定义client_id
            client_secret: 可选的自定义client_secret
        """
        self.cookie = cookie
        self.client_id = client_id or self.CLIENT_ID
        self.client_secret = client_secret or self.CLIENT_SECRET
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """配置请求会话"""
        self.session.headers.update({
            'User-Agent': self.MOBILE_USER_AGENT,
            'Cookie': self.cookie,
            'Referer': 'https://pan.baidu.com',
        })
    
    def _parse_cookie(self) -> Dict[str, str]:
        """解析Cookie字符串为字典"""
        cookie_dict = {}
        for item in self.cookie.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookie_dict[key.strip()] = value.strip()
        return cookie_dict
    
    def _get_bduss(self) -> Optional[str]:
        """获取BDUSS"""
        cookie_dict = self._parse_cookie()
        return cookie_dict.get('BDUSS')
    
    def _get_stoken(self) -> Optional[str]:
        """获取STOKEN"""
        cookie_dict = self._parse_cookie()
        return cookie_dict.get('STOKEN')
    
    def get_file_list(self, dir_path: str = "/", page: int = 1, size: int = 100) -> Dict:
        """
        获取文件列表
        
        Args:
            dir_path: 目录路径
            page: 页码
            size: 每页数量
            
        Returns:
            文件列表数据
        """
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
            
            if data.get('errno') == 0:
                logger.info(f"获取文件列表成功: {dir_path}, 文件数: {len(data.get('list', []))}")
                return data
            else:
                logger.error(f"获取文件列表失败: errno={data.get('errno')}, {data.get('errmsg')}")
                return {'errno': data.get('errno'), 'list': []}
        except Exception as e:
            logger.error(f"获取文件列表异常: {e}")
            return {'errno': -1, 'list': []}
    
    def get_file_info(self, fs_id: str) -> Optional[Dict]:
        """
        获取文件详细信息
        
        Args:
            fs_id: 文件ID
            
        Returns:
            文件信息
        """
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
            else:
                logger.error(f"获取文件信息失败: {data}")
                return None
        except Exception as e:
            logger.error(f"获取文件信息异常: {e}")
            return None
    
    def get_download_link(self, fs_id: str, use_crack: bool = True) -> Optional[str]:
        """
        获取下载链接
        
        Args:
            fs_id: 文件ID
            use_crack: 是否使用crack_video接口
            
        Returns:
            下载链接
        """
        if use_crack:
            return self._get_crack_video_link(fs_id)
        else:
            return self._get_standard_link(fs_id)
    
    def _get_crack_video_link(self, fs_id: str) -> Optional[str]:
        """
        使用crack_video接口获取视频播放地址（核心方法）
        这是百度网盘的视频破解接口，可以获取直接可播放的URL
        
        Args:
            fs_id: 文件ID
            
        Returns:
            视频播放URL
        """
        # 先获取文件信息
        file_info = self.get_file_info(fs_id)
        if not file_info:
            logger.error("无法获取文件信息")
            return None
        
        path = file_info.get('path')
        if not path:
            logger.error("文件路径为空")
            return None
        
        # 使用streaming接口获取视频地址
        url = f"{self.D_PCS_URL}/rest/2.0/pcs/file"
        params = {
            'method': 'streaming',
            'path': path,
            'type': 'M3U8_AUTO_480',  # 视频质量
            'access_token': self._get_access_token(),
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30, allow_redirects=False)
            
            # 检查是否是302重定向
            if response.status_code == 302:
                play_url = response.headers.get('Location')
                if play_url:
                    logger.info(f"获取crack_video播放地址成功: {play_url[:100]}...")
                    return play_url
            
            # 尝试从响应体获取
            if response.status_code == 200:
                data = response.json()
                if 'urls' in data and data['urls']:
                    play_url = data['urls'][0]['url']
                    logger.info(f"获取crack_video播放地址成功: {play_url[:100]}...")
                    return play_url
            
            logger.error(f"获取crack_video地址失败: status={response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"获取crack_video地址异常: {e}")
            return None
    
    def _get_standard_link(self, fs_id: str) -> Optional[str]:
        """
        使用标准接口获取下载链接
        
        Args:
            fs_id: 文件ID
            
        Returns:
            下载链接
        """
        file_info = self.get_file_info(fs_id)
        if not file_info:
            return None
        
        dlink = file_info.get('dlink')
        if dlink:
            logger.info(f"获取标准下载链接成功: {dlink[:100]}...")
            return dlink
        
        return None
    
    def _get_access_token(self) -> str:
        """
        获取access_token
        这里简化处理，实际应该实现完整的OAuth流程
        """
        # 简化版：尝试从cookie中提取或使用固定值
        # 实际项目中应该实现完整的token刷新逻辑
        return ""
    
    def parse_share_link(self, share_url: str, pwd: str = "") -> Optional[Dict]:
        """
        解析分享链接
        
        Args:
            share_url: 分享链接 (如: https://pan.baidu.com/s/1xxxxx)
            pwd: 提取码
            
        Returns:
            分享信息
        """
        # 提取surl
        parsed = urlparse(share_url)
        path_parts = parsed.path.split('/')
        surl = None
        
        for part in path_parts:
            if part and part != 's':
                surl = part
                break
        
        if not surl:
            logger.error(f"无法从链接提取surl: {share_url}")
            return None
        
        # 如果URL中包含提取码参数
        if not pwd and parsed.query:
            query_params = parse_qs(parsed.query)
            pwd = query_params.get('pwd', [''])[0]
        
        logger.info(f"解析分享链接: surl={surl}, pwd={pwd}")
        
        # 验证提取码并获取分享信息
        return self._verify_share(surl, pwd)
    
    def _verify_share(self, surl: str, pwd: str) -> Optional[Dict]:
        """
        验证分享链接并获取信息
        
        Args:
            surl: 分享ID
            pwd: 提取码
            
        Returns:
            分享信息
        """
        url = f"{self.BASE_URL}/share/verify"
        params = {
            'surl': surl,
            'pwd': pwd,
            't': int(time.time() * 1000),
            'web': 1,
        }
        
        try:
            response = self.session.post(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('errno') == 0:
                logger.info(f"验证分享成功: surl={surl}")
                return {
                    'surl': surl,
                    'pwd': pwd,
                    'randsk': data.get('randsk', ''),
                    'share_id': data.get('shareid', ''),
                }
            else:
                logger.error(f"验证分享失败: {data}")
                return None
        except Exception as e:
            logger.error(f"验证分享异常: {e}")
            return None
    
    def get_share_file_list(self, surl: str, pwd: str, dir_path: str = "/") -> Dict:
        """
        获取分享文件列表
        
        Args:
            surl: 分享ID
            pwd: 提取码
            dir_path: 目录路径
            
        Returns:
            文件列表
        """
        # 先验证分享
        share_info = self._verify_share(surl, pwd)
        if not share_info:
            return {'errno': -1, 'list': []}
        
        url = f"{self.BASE_URL}/share/list"
        params = {
            'shareid': share_info['share_id'],
            'dir': dir_path,
            'web': 1,
            'page': 1,
            'num': 100,
        }
        
        # 添加randsk到cookie
        self.session.cookies.set('BDCLND', share_info['randsk'])
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('errno') == 0:
                logger.info(f"获取分享文件列表成功: {len(data.get('list', []))}个文件")
                return data
            else:
                logger.error(f"获取分享文件列表失败: {data}")
                return {'errno': data.get('errno'), 'list': []}
        except Exception as e:
            logger.error(f"获取分享文件列表异常: {e}")
            return {'errno': -1, 'list': []}


class BaiduPanPlayer:
    """百度网盘播放器服务"""
    
    def __init__(self, cookie: str):
        """
        初始化播放器服务
        
        Args:
            cookie: 百度网盘Cookie
        """
        self.api = BaiduPanAPI(cookie)
    
    def get_play_url(self, file_path: str = None, fs_id: str = None, 
                     share_url: str = None, pwd: str = "") -> Dict:
        """
        获取播放地址（统一入口）
        
        Args:
            file_path: 文件路径 (如: /视频/电影.mp4)
            fs_id: 文件ID
            share_url: 分享链接
            pwd: 提取码
            
        Returns:
            播放信息字典，格式适配com.fongmi.android.tv客户端
        """
        try:
            # 1. 如果是分享链接
            if share_url:
                return self._get_play_url_from_share(share_url, pwd)
            
            # 2. 如果提供了fs_id
            if fs_id:
                return self._get_play_url_from_fs_id(fs_id)
            
            # 3. 如果提供了文件路径
            if file_path:
                return self._get_play_url_from_path(file_path)
            
            return self._error_response("请提供文件路径、fs_id或分享链接")
            
        except Exception as e:
            logger.error(f"获取播放地址异常: {e}", exc_info=True)
            return self._error_response(str(e))
    
    def _get_play_url_from_fs_id(self, fs_id: str) -> Dict:
        """从文件ID获取播放地址"""
        logger.info(f"从fs_id获取播放地址: {fs_id}")
        
        # 获取文件信息
        file_info = self.api.get_file_info(fs_id)
        if not file_info:
            return self._error_response("无法获取文件信息")
        
        # 使用crack_video接口获取播放地址
        play_url = self.api.get_download_link(fs_id, use_crack=True)
        if not play_url:
            # 如果crack失败，尝试标准接口
            play_url = self.api.get_download_link(fs_id, use_crack=False)
        
        if not play_url:
            return self._error_response("无法获取播放地址")
        
        return self._success_response(play_url, file_info)
    
    def _get_play_url_from_path(self, file_path: str) -> Dict:
        """从文件路径获取播放地址"""
        logger.info(f"从路径获取播放地址: {file_path}")
        
        # 获取父目录
        import os
        dir_path = os.path.dirname(file_path)
        file_name = os.path.basename(file_path)
        
        # 列出目录文件
        file_list_data = self.api.get_file_list(dir_path)
        if file_list_data.get('errno') != 0:
            return self._error_response("无法列出目录文件")
        
        # 查找目标文件
        target_file = None
        for file_item in file_list_data.get('list', []):
            if file_item.get('server_filename') == file_name:
                target_file = file_item
                break
        
        if not target_file:
            return self._error_response(f"找不到文件: {file_name}")
        
        fs_id = target_file.get('fs_id')
        if not fs_id:
            return self._error_response("文件ID为空")
        
        # 使用fs_id获取播放地址
        return self._get_play_url_from_fs_id(str(fs_id))
    
    def _get_play_url_from_share(self, share_url: str, pwd: str) -> Dict:
        """从分享链接获取播放地址"""
        logger.info(f"从分享链接获取播放地址: {share_url}")
        
        # 解析分享链接
        share_info = self.api.parse_share_link(share_url, pwd)
        if not share_info:
            return self._error_response("无法解析分享链接或提取码错误")
        
        # 获取分享文件列表
        file_list_data = self.api.get_share_file_list(
            share_info['surl'], 
            share_info['pwd']
        )
        
        if file_list_data.get('errno') != 0:
            return self._error_response("无法获取分享文件列表")
        
        files = file_list_data.get('list', [])
        if not files:
            return self._error_response("分享中没有文件")
        
        # 找到第一个视频文件
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.rmvb', '.m3u8', '.ts'}
        target_file = None
        
        for file_item in files:
            if file_item.get('isdir') == 0:  # 不是目录
                filename = file_item.get('server_filename', '')
                ext = os.path.splitext(filename)[1].lower()
                if ext in video_extensions:
                    target_file = file_item
                    break
        
        if not target_file:
            # 如果没有找到视频，返回第一个文件
            target_file = files[0]
        
        fs_id = target_file.get('fs_id')
        if not fs_id:
            return self._error_response("文件ID为空")
        
        # 对于分享文件，需要特殊处理
        # 这里简化处理，实际可能需要转存到自己网盘
        logger.warning("分享文件暂不支持直接获取播放地址，建议先转存")
        return self._error_response("分享文件需要先转存到自己的网盘")
    
    def _success_response(self, play_url: str, file_info: Dict = None) -> Dict:
        """
        构建成功响应（适配com.fongmi.android.tv客户端格式）
        
        Args:
            play_url: 播放地址
            file_info: 文件信息
            
        Returns:
            响应字典
        """
        response = {
            'parse': 0,  # 不需要解析
            'playUrl': '',
            'url': play_url,
            'header': {
                'User-Agent': 'netdisk',  # 关键：使用netdisk UA
                'Referer': 'https://pan.baidu.com',
            }
        }
        
        # 添加文件信息
        if file_info:
            response['name'] = file_info.get('server_filename', '')
            response['size'] = file_info.get('size', 0)
        
        return response
    
    def _error_response(self, message: str) -> Dict:
        """
        构建错误响应
        
        Args:
            message: 错误消息
            
        Returns:
            错误响应字典
        """
        return {
            'error': True,
            'message': message,
            'url': '',
            'parse': 0,
        }


# ============= Flask API 路由 =============

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'service': 'baidu-pan-player'})


@app.route('/play', methods=['GET', 'POST'])
def play():
    """
    获取播放地址
    
    Query参数或JSON参数:
        - cookie: 百度网盘Cookie (必需)
        - file_path: 文件路径 (可选)
        - fs_id: 文件ID (可选)
        - share_url: 分享链接 (可选)
        - pwd: 提取码 (可选)
    
    返回:
        JSON格式的播放信息
    """
    try:
        # 获取参数
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()
        
        cookie = data.get('cookie')
        if not cookie:
            return jsonify({'error': True, 'message': 'Cookie不能为空'}), 400
        
        file_path = data.get('file_path') or data.get('path')
        fs_id = data.get('fs_id') or data.get('fsid')
        share_url = data.get('share_url') or data.get('url')
        pwd = data.get('pwd', '')
        
        # 创建播放器实例
        player = BaiduPanPlayer(cookie)
        
        # 获取播放地址
        result = player.get_play_url(
            file_path=file_path,
            fs_id=fs_id,
            share_url=share_url,
            pwd=pwd
        )
        
        # 记录日志
        if result.get('error'):
            logger.warning(f"获取播放地址失败: {result.get('message')}")
            return jsonify(result), 400
        else:
            logger.info(f"获取播放地址成功")
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"处理播放请求异常: {e}", exc_info=True)
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/list', methods=['GET', 'POST'])
def list_files():
    """
    列出文件
    
    Query参数或JSON参数:
        - cookie: 百度网盘Cookie (必需)
        - dir: 目录路径 (默认为/)
        - page: 页码 (默认为1)
        - size: 每页数量 (默认为100)
    """
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
        else:
            data = request.args.to_dict()
        
        cookie = data.get('cookie')
        if not cookie:
            return jsonify({'error': True, 'message': 'Cookie不能为空'}), 400
        
        dir_path = data.get('dir', '/')
        page = int(data.get('page', 1))
        size = int(data.get('size', 100))
        
        # 创建API实例
        api = BaiduPanAPI(cookie)
        
        # 获取文件列表
        result = api.get_file_list(dir_path, page, size)
        
        if result.get('errno') == 0:
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"列出文件异常: {e}", exc_info=True)
        return jsonify({'error': True, 'message': str(e)}), 500


@app.route('/info', methods=['GET'])
def info():
    """API信息"""
    return jsonify({
        'name': '百度网盘播放地址提取服务',
        'version': '1.0.0',
        'description': '直接调用百度网盘crack_video API获取可播放地址',
        'client': 'com.fongmi.android.tv',
        'endpoints': {
            'health': '/health - 健康检查',
            'play': '/play - 获取播放地址',
            'list': '/list - 列出文件',
            'info': '/info - API信息',
        },
        'usage': {
            'play': {
                'method': 'GET or POST',
                'params': {
                    'cookie': 'BDUSS=xxx; STOKEN=xxx (必需)',
                    'file_path': '/视频/电影.mp4 (可选)',
                    'fs_id': '文件ID (可选)',
                    'share_url': 'https://pan.baidu.com/s/1xxxxx (可选)',
                    'pwd': '提取码 (可选)',
                },
                'example': '/play?cookie=BDUSS=xxx&file_path=/视频/电影.mp4'
            }
        }
    })


if __name__ == '__main__':
    import os
    
    # 从环境变量获取配置
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"启动百度网盘播放服务: http://{host}:{port}")
    logger.info("API文档: http://{host}:{port}/info")
    
    app.run(host=host, port=port, debug=debug)
