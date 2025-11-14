#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度网盘播放服务测试客户端
模拟com.fongmi.android.tv影视客户端的调用
"""

import requests
import json
import sys


class BaiduPanClient:
    """百度网盘播放服务客户端"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        """
        初始化客户端
        
        Args:
            base_url: 服务地址
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"健康检查失败: {e}")
            return False
    
    def get_play_url(self, cookie: str, file_path: str = None, 
                     fs_id: str = None, share_url: str = None, 
                     pwd: str = "") -> dict:
        """
        获取播放地址
        
        Args:
            cookie: 百度网盘Cookie
            file_path: 文件路径
            fs_id: 文件ID
            share_url: 分享链接
            pwd: 提取码
            
        Returns:
            播放信息字典
        """
        url = f"{self.base_url}/play"
        data = {
            'cookie': cookie,
        }
        
        if file_path:
            data['file_path'] = file_path
        if fs_id:
            data['fs_id'] = fs_id
        if share_url:
            data['share_url'] = share_url
            data['pwd'] = pwd
        
        try:
            response = self.session.post(
                url,
                json=data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                print("\n✅ 获取播放地址成功!")
                self._print_play_info(result)
                return result
            else:
                error = response.json()
                print(f"\n❌ 获取播放地址失败: {error.get('message')}")
                return error
                
        except Exception as e:
            print(f"\n❌ 请求异常: {e}")
            return {'error': True, 'message': str(e)}
    
    def list_files(self, cookie: str, dir_path: str = "/", 
                   page: int = 1, size: int = 20) -> dict:
        """
        列出文件
        
        Args:
            cookie: 百度网盘Cookie
            dir_path: 目录路径
            page: 页码
            size: 每页数量
            
        Returns:
            文件列表
        """
        url = f"{self.base_url}/list"
        params = {
            'cookie': cookie,
            'dir': dir_path,
            'page': page,
            'size': size,
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                print(f"\n✅ 获取文件列表成功! 目录: {dir_path}")
                self._print_file_list(result)
                return result
            else:
                error = response.json()
                print(f"\n❌ 获取文件列表失败: {error}")
                return error
                
        except Exception as e:
            print(f"\n❌ 请求异常: {e}")
            return {'error': True, 'message': str(e)}
    
    def _print_play_info(self, info: dict):
        """打印播放信息"""
        print("\n" + "="*60)
        print("播放信息")
        print("="*60)
        
        if info.get('error'):
            print(f"❌ 错误: {info.get('message')}")
            return
        
        print(f"📺 文件名: {info.get('name', 'N/A')}")
        print(f"📦 文件大小: {self._format_size(info.get('size', 0))}")
        print(f"🔗 播放地址: {info.get('url', '')[:80]}...")
        print(f"\n📋 Headers:")
        for key, value in info.get('header', {}).items():
            print(f"   {key}: {value}")
        print(f"\n🎬 解析状态: {'需要解析' if info.get('parse', 0) else '直接播放'}")
        print("="*60)
    
    def _print_file_list(self, data: dict):
        """打印文件列表"""
        files = data.get('list', [])
        
        print("\n" + "="*60)
        print(f"文件列表 (共 {len(files)} 个)")
        print("="*60)
        
        for i, file_item in enumerate(files, 1):
            is_dir = file_item.get('isdir', 0) == 1
            icon = "📁" if is_dir else "📄"
            name = file_item.get('server_filename', 'Unknown')
            size = self._format_size(file_item.get('size', 0))
            fs_id = file_item.get('fs_id', 'N/A')
            
            print(f"{i:2d}. {icon} {name}")
            if not is_dir:
                print(f"     📦 大小: {size} | 🆔 fs_id: {fs_id}")
        
        print("="*60)
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size_float = float(size)
        
        while size_float >= 1024 and unit_index < len(units) - 1:
            size_float /= 1024
            unit_index += 1
        
        return f"{size_float:.2f} {units[unit_index]}"


def print_usage():
    """打印使用说明"""
    print("""
百度网盘播放服务测试客户端
======================================

使用方法:

1. 健康检查:
   python test_client.py health

2. 列出文件:
   python test_client.py list <cookie> [dir_path]
   
   示例:
   python test_client.py list "BDUSS=xxx; STOKEN=xxx" "/"
   python test_client.py list "BDUSS=xxx; STOKEN=xxx" "/视频"

3. 获取播放地址 (通过文件路径):
   python test_client.py play <cookie> path <file_path>
   
   示例:
   python test_client.py play "BDUSS=xxx; STOKEN=xxx" path "/视频/电影.mp4"

4. 获取播放地址 (通过文件ID):
   python test_client.py play <cookie> fsid <fs_id>
   
   示例:
   python test_client.py play "BDUSS=xxx; STOKEN=xxx" fsid "123456789"

5. 获取播放地址 (通过分享链接):
   python test_client.py play <cookie> share <share_url> [pwd]
   
   示例:
   python test_client.py play "BDUSS=xxx; STOKEN=xxx" share "https://pan.baidu.com/s/1xxxxx" "1234"

注意:
- Cookie格式: BDUSS=xxx; STOKEN=xxx
- 确保服务已启动: python baidu_pan_player.py
- 默认服务地址: http://localhost:5000
""")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_usage()
        return
    
    # 创建客户端
    client = BaiduPanClient()
    
    command = sys.argv[1]
    
    # 健康检查
    if command == 'health':
        print("🔍 检查服务状态...")
        if client.health_check():
            print("✅ 服务正常运行")
        else:
            print("❌ 服务未响应")
        return
    
    # 列出文件
    if command == 'list':
        if len(sys.argv) < 3:
            print("❌ 缺少Cookie参数")
            print_usage()
            return
        
        cookie = sys.argv[2]
        dir_path = sys.argv[3] if len(sys.argv) > 3 else "/"
        
        client.list_files(cookie, dir_path)
        return
    
    # 获取播放地址
    if command == 'play':
        if len(sys.argv) < 4:
            print("❌ 参数不足")
            print_usage()
            return
        
        cookie = sys.argv[2]
        play_type = sys.argv[3]
        
        if play_type == 'path':
            if len(sys.argv) < 5:
                print("❌ 缺少文件路径")
                return
            file_path = sys.argv[4]
            client.get_play_url(cookie, file_path=file_path)
        
        elif play_type == 'fsid':
            if len(sys.argv) < 5:
                print("❌ 缺少文件ID")
                return
            fs_id = sys.argv[4]
            client.get_play_url(cookie, fs_id=fs_id)
        
        elif play_type == 'share':
            if len(sys.argv) < 5:
                print("❌ 缺少分享链接")
                return
            share_url = sys.argv[4]
            pwd = sys.argv[5] if len(sys.argv) > 5 else ""
            client.get_play_url(cookie, share_url=share_url, pwd=pwd)
        
        else:
            print(f"❌ 未知的播放类型: {play_type}")
            print_usage()
        
        return
    
    # 未知命令
    print(f"❌ 未知命令: {command}")
    print_usage()


if __name__ == '__main__':
    main()
