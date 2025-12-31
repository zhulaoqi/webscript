"""
工具函数
"""
import os
import time
import random
import requests
import zipfile
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
import json
from tqdm import tqdm
import boto3
from botocore.exceptions import ClientError
from config import DOWNLOAD_CONFIG, USER_AGENTS, AWS_S3_CONFIG


class S3Uploader:
    """S3上传工具类"""
    
    def __init__(self):
        """初始化S3客户端"""
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_S3_CONFIG['access_key_id'],
            aws_secret_access_key=AWS_S3_CONFIG['secret_access_key'],
            region_name=AWS_S3_CONFIG['region']
        )
        self.bucket_name = AWS_S3_CONFIG['bucket_name']
        self.cdn_prefix = AWS_S3_CONFIG['url_prefix']
    
    def upload_file(self, local_path: str, s3_key: str) -> Optional[str]:
        """
        上传文件到S3
        
        Args:
            local_path: 本地文件路径
            s3_key: S3对象键名
            
        Returns:
            CDN URL或None
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(local_path):
                print(f"⚠️  本地文件不存在: {local_path}")
                return None
            
            # 确定Content-Type
            content_type = self._get_content_type(local_path)
            
            print(f"    📤 上传中: {os.path.basename(local_path)} -> S3")
            
            # 上传文件（不使用ACL，存储桶已配置为公开访问）
            self.s3_client.upload_file(
                local_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type
                }
            )
            
            # 返回CDN URL
            cdn_url = f"{self.cdn_prefix}{s3_key}"
            print(f"    ✅ S3成功: {cdn_url}")
            return cdn_url
            
        except ClientError as e:
            print(f"    ❌ S3上传失败: {e}")
            return None
        except Exception as e:
            print(f"    ❌ 上传错误: {e}")
            return None
    
    @staticmethod
    def _get_content_type(file_path: str) -> str:
        """根据文件扩展名获取Content-Type"""
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
        }
        return content_types.get(ext, 'application/octet-stream')


class DownloadUtils:
    """下载工具类"""
    
    @staticmethod
    def get_random_user_agent() -> str:
        """获取随机User-Agent"""
        return random.choice(USER_AGENTS)
    
    @staticmethod
    def random_delay():
        """随机延迟"""
        delay = random.uniform(
            DOWNLOAD_CONFIG['delay_min'], 
            DOWNLOAD_CONFIG['delay_max']
        )
        time.sleep(delay)
    
    @staticmethod
    def download_file(url: str, save_path: str, proxies: Optional[Dict] = None, referer: str = None) -> bool:
        """
        下载文件（支持防盗链突破）
        
        Args:
            url: 文件URL
            save_path: 保存路径
            proxies: 代理配置
            referer: 来源页面（用于突破防盗链）
            
        Returns:
            是否下载成功
        """
        # 跳过blob和data URLs
        if url.startswith('blob:') or url.startswith('data:'):
            return False
        
        # 跳过用户头像、图标等非素材内容
        skip_patterns = [
            'profile-image', 'avatar', 'user-avatar', 'user_avatar',
            'favicon', 'logo', 'icon', 'thumbnail_placeholder',
            '/users/', '/user/', '/profile/', '/creator/',
        ]
        url_lower = url.lower()
        for pattern in skip_patterns:
            if pattern in url_lower:
                return False
        
        max_retries = DOWNLOAD_CONFIG['max_retries']
        timeout = 60  # 增加超时时间到60秒
        
        # 根据URL推断来源网站
        if not referer:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            referer = f"{parsed.scheme}://{parsed.netloc}/"
        
        for attempt in range(max_retries):
            try:
                # 增强请求头，模拟真实浏览器
                headers = {
                    'User-Agent': DownloadUtils.get_random_user_agent(),
                    'Referer': referer,  # 使用正确的来源页面
                    'Accept': '*/*',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'video' if '.mp4' in url or '.mov' in url else 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'same-origin',
                }
                
                # 动态超时：连接超时15秒，读取超时60秒
                response = requests.get(
                    url, 
                    headers=headers, 
                    proxies=proxies,
                    timeout=(15, 60),  # (connect timeout, read timeout)
                    stream=True,
                    allow_redirects=True  # 允许重定向
                )
                response.raise_for_status()
                
                # 检查Content-Type，确保不是HTML错误页
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' in content_type:
                    return False
                
                # 确保目录存在
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                
                # 下载文件
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                
                with open(save_path, 'wb') as f:
                    if total_size == 0:
                        content = response.content
                        f.write(content)
                        downloaded_size = len(content)
                    else:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded_size += len(chunk)
                
                # 验证下载完整性
                if total_size > 0 and downloaded_size < total_size * 0.9:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return False
                
                # 检查文件大小（至少1KB，避免下载到错误页面）
                if downloaded_size < 1024:
                    return False
                
                return True
                
            except requests.exceptions.Timeout as e:
                # 超时错误，静默重试
                if attempt < max_retries - 1:
                    time.sleep(3)  # 等待3秒后重试
                    continue
                return False
            except requests.exceptions.ConnectionError as e:
                # 连接错误，静默重试
                if attempt < max_retries - 1:
                    time.sleep(3)
                    continue
                return False
            except Exception as e:
                # 其他错误
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                    continue
                return False
                    
        return False
    
    @staticmethod
    def get_file_extension(url: str) -> str:
        """从URL获取文件扩展名"""
        parsed = urlparse(url)
        path = parsed.path
        ext = os.path.splitext(path)[1]
        if not ext:
            # 尝试从查询参数获取
            if 'format=' in url:
                ext = '.' + url.split('format=')[1].split('&')[0]
            else:
                ext = '.mp4'  # 默认视频格式
        return ext


class DataManager:
    """数据管理类"""
    
    def __init__(self, output_dir: str, use_s3: bool = True):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        self.text2video_dir = self.output_dir / 'text2video'
        self.image2video_dir = self.output_dir / 'image2video'
        self.text2video_dir.mkdir(exist_ok=True)
        self.image2video_dir.mkdir(exist_ok=True)
        
        # 数据存储
        self.text2video_data: List[Dict] = []
        self.image2video_data: List[Dict] = []
        
        # S3上传器
        self.use_s3 = use_s3
        if use_s3:
            self.s3_uploader = S3Uploader()
            print("✓ S3上传已启用")
    
    def upload_to_s3(self, local_path: str, category: str, filename: str) -> Optional[str]:
        """
        上传文件到S3并返回URL
        
        Args:
            local_path: 本地文件路径
            category: 分类（用于S3路径）
            filename: 文件名
            
        Returns:
            S3 CDN URL
        """
        if not self.use_s3 or not local_path or not os.path.exists(local_path):
            return None
        
        # 生成S3键名: video-materials/文件名 (不再包含网站分类)
        if category:
            s3_key = f"video-materials/{category}/{filename}"
        else:
            s3_key = f"video-materials/{filename}"
        
        # 上传并获取URL
        cdn_url = self.s3_uploader.upload_file(local_path, s3_key)
        
        return cdn_url
    
    def add_text2video(self, data: Dict):
        """添加文生视频数据"""
        self.text2video_data.append(data)
        print(f"    💾 数据已保存 (总计: {len(self.text2video_data)} 条)")
    
    def add_image2video(self, data: Dict):
        """添加图生视频数据"""
        self.image2video_data.append(data)
        print(f"    💾 数据已保存 (总计: {len(self.image2video_data)} 条)")
    
    def save_json(self):
        """保存JSON数据（仅用于调试）"""
        pass  # 不再输出JSON文件
    
    def create_zip(self):
        """创建ZIP压缩包"""
        pass  # 不再创建ZIP
    
    def append_to_txt(self, work_url: str, site_name: str, source_url: str = '', prompt: str = '', cover_url: str = ''):
        """
        实时追加数据到TXT文件
        格式：作品URL 原图URL 提示词 缩略图URL（固定4列，空格分隔）
        
        Args:
            work_url: 作品URL（视频或图片）
            site_name: 网站名称
            source_url: 原图URL（图生视频/图生图的输入图）
            prompt: 提示词
            cover_url: 缩略图URL（视频封面）
        """
        try:
            # 清理提示词（去掉换行符，限制长度）
            if prompt:
                prompt = prompt.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                # 去除多余空格
                prompt = ' '.join(prompt.split())
                # 限制长度
                if len(prompt) > 500:
                    prompt = prompt[:500]
            
            # 固定4列格式
            line = f"{work_url} {source_url or '无原图'} {prompt or '无提示词'} {cover_url or '无缩略图'}\n"
            
            # 网站专用文件
            site_normalized = site_name.lower().replace(' ', '_').replace('.', '_')
            site_txt_path = self.output_dir.parent / f'{site_normalized}.txt'
            
            # 追加到网站文件
            with open(site_txt_path, 'a', encoding='utf-8') as f:
                f.write(line)
            
            # 追加到总文件
            all_txt_path = self.output_dir.parent / 'all_materials.txt'
            with open(all_txt_path, 'a', encoding='utf-8') as f:
                f.write(line)
                
        except Exception as e:
            print(f"  ⚠️  写入TXT失败: {e}")
    
    def export_txt(self, site_name: str = None):
        """
        导出TXT文件 - 每行一个S3 URL，效率更高（已废弃，改用实时写入）
        
        Args:
            site_name: 网站名称，如果提供则只导出该网站数据
        """
        try:
            print(f"\n  📝 导出TXT: site_name={site_name}")
            print(f"  📁 数据统计: text2video={len(self.text2video_data)}, image2video={len(self.image2video_data)}")
            
            # 收集所有URL
            all_urls = []
            
            # 添加文生视频数据的URL
            for item in self.text2video_data:
                category = item.get('category', '')
                
                # 如果指定了site_name，只导出匹配的数据
                if site_name:
                    site_normalized = site_name.lower().replace('_', ' ')
                    category_normalized = category.lower().replace('_', ' ')
                    if site_normalized not in category_normalized and category_normalized not in site_normalized:
                        continue
                
                # 添加视频URL
                if item.get('video_s3_url'):
                    all_urls.append(item.get('video_s3_url'))
                
                # 添加缩略图URL
                if item.get('thumbnail_s3_url'):
                    all_urls.append(item.get('thumbnail_s3_url'))
            
            # 添加图生视频数据的URL
            for item in self.image2video_data:
                category = item.get('category', '')
                
                # 如果指定了site_name，只导出匹配的数据
                if site_name:
                    site_normalized = site_name.lower().replace('_', ' ')
                    category_normalized = category.lower().replace('_', ' ')
                    if site_normalized not in category_normalized and category_normalized not in site_normalized:
                        continue
                
                # 添加原图URL
                if item.get('source_image_s3_url'):
                    all_urls.append(item.get('source_image_s3_url'))
                
                # 添加视频URL
                if item.get('video_s3_url'):
                    all_urls.append(item.get('video_s3_url'))
                
                # 添加缩略图URL
                if item.get('thumbnail_s3_url'):
                    all_urls.append(item.get('thumbnail_s3_url'))
            
            print(f"  🔗 收集到 {len(all_urls)} 个S3链接")
            
            if not all_urls:
                print(f"  ⚠️  没有数据可导出 (site: {site_name})")
                return None
            
            # 生成文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            if site_name:
                filename = f'{site_name}_{timestamp}.txt'
            else:
                filename = f'all_materials_{timestamp}.txt'
            
            txt_path = self.output_dir.parent / filename
            
            # 写入TXT文件（每行一个URL）
            with open(txt_path, 'w', encoding='utf-8') as f:
                for url in all_urls:
                    f.write(url + '\n')
            
            print(f"  ✅ TXT已导出: {txt_path}")
            print(f"  📊 S3链接数: {len(all_urls)} 条")
            return txt_path
            
        except Exception as e:
            print(f"✗ 导出TXT失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_summary(self) -> Dict:
        """获取数据摘要"""
        return {
            'text2video_count': len(self.text2video_data),
            'image2video_count': len(self.image2video_data),
            'total_count': len(self.text2video_data) + len(self.image2video_data)
        }


def setup_proxy(proxy_config: Dict) -> Optional[Dict]:
    """
    设置代理
    
    Args:
        proxy_config: 代理配置
        
    Returns:
        requests代理字典
    """
    if not proxy_config.get('host'):
        return None
    
    if proxy_config.get('user') and proxy_config.get('password'):
        proxy_url = f"http://{proxy_config['user']}:{proxy_config['password']}@{proxy_config['host']}"
        if proxy_config.get('port'):
            proxy_url += f":{proxy_config['port']}"
    else:
        proxy_url = f"http://{proxy_config['host']}"
        if proxy_config.get('port'):
            proxy_url += f":{proxy_config['port']}"
    
    return {
        'http': proxy_url,
        'https': proxy_url
    }

