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
        
        # Excel 数据存储（内存中维护）
        self.excel_data: Dict[str, List[List]] = {}  # {site_name: [[row1], [row2], ...]}
        
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
    
    
    def append_to_txt(self, work_url: str, site_name: str, source_url: str = '', prompt: str = '', cover_url: str = ''):
        """
        实时追加数据到 Excel 数据（内存中）
        
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
            
            # 网站标识
            site_normalized = site_name.lower().replace(' ', '_').replace('.', '_')
            
            # 添加到 Excel 数据（内存中）
            if site_normalized not in self.excel_data:
                self.excel_data[site_normalized] = []
            
            self.excel_data[site_normalized].append([
                work_url,
                source_url or '无原图',
                prompt or '无提示词',
                cover_url or '无缩略图'
            ])
            
            # 同时添加到总数据
            if 'all_materials' not in self.excel_data:
                self.excel_data['all_materials'] = []
            
            self.excel_data['all_materials'].append([
                work_url,
                source_url or '无原图',
                prompt or '无提示词',
                cover_url or '无缩略图'
            ])
                
        except Exception as e:
            print(f"  ⚠️  写入数据失败: {e}")
    
    def save_excel(self):
        """
        保存 Excel 文件（从内存中的数据）
        每个网站一个 Excel 文件，加一个总的 all_materials.xlsx
        格式：作品URL | 原图URL | 提示词 | 缩略图URL
        """
        try:
            if not self.excel_data:
                print("  ℹ️  没有数据需要保存到 Excel")
                return
            
            print(f"\n📊 生成 Excel 文件...")
            
            for site_name, rows in self.excel_data.items():
                if not rows:
                    continue
                
                # 创建工作簿
                wb = Workbook()
                ws = wb.active
                ws.title = "素材数据"
                
                # 设置表头
                headers = ["作品URL", "原图URL", "提示词", "缩略图URL"]
                ws.append(headers)
                
                # 设置表头样式
                for cell in ws[1]:
                    cell.font = Font(bold=True, size=12)
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # 添加数据
                print(f"  📝 开始写入 {len(rows)} 行数据到Excel...")
                for row_idx, row in enumerate(rows, start=1):
                    # 检查提示词列（第3列）
                    if len(row) >= 3:
                        prompt = row[2]
                        if row_idx <= 3:  # 只打印前3行
                            print(f"    行{row_idx} - 提示词长度: {len(str(prompt))} 字符")
                            print(f"           前50字符: {str(prompt)[:50]}")
                    ws.append(row)
                
                # 设置单元格样式：文本换行 + 估算行高
                for row_idx, row_cells in enumerate(ws.iter_rows(min_row=2), start=2):
                    max_text_length = 0
                    for cell_idx, cell in enumerate(row_cells):
                        cell.alignment = Alignment(wrap_text=True, vertical='top')
                        # 检查第3列（提示词）的文本长度
                        if cell_idx == 2 and cell.value:  # 第3列是提示词
                            text_length = len(str(cell.value))
                            max_text_length = max(max_text_length, text_length)
                    
                    # 根据提示词长度设置行高
                    if max_text_length > 80:
                        # 估算行高：每80字符一行，每行15磅
                        estimated_lines = (max_text_length // 80) + 1
                        ws.row_dimensions[row_idx].height = min(estimated_lines * 15, 300)  # 最高300磅
                    else:
                        ws.row_dimensions[row_idx].height = 30  # 默认行高
                
                # 自动调整列宽（提示词列特殊处理）
                for col_idx, column in enumerate(ws.columns, start=1):
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    # 第3列是提示词，设置固定宽度80
                    if col_idx == 3:
                        ws.column_dimensions[column_letter].width = 80
                    else:
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 100)
                        ws.column_dimensions[column_letter].width = adjusted_width
                
                # 保存文件
                excel_path = self.output_dir.parent / f'{site_name}.xlsx'
                wb.save(excel_path)
                print(f"  ✅ {site_name}.xlsx ({len(rows)} 条)")
                
                # 【验证】读取保存的文件，检查提示词是否完整
                print(f"  🔍 验证Excel文件...")
                wb_check = load_workbook(excel_path)
                ws_check = wb_check.active
                for row_idx in range(2, min(4, ws_check.max_row + 1)):  # 检查前2行数据
                    cell_value = ws_check.cell(row_idx, 3).value  # 第3列是提示词
                    if cell_value:
                        print(f"    行{row_idx-1} 提示词长度: {len(str(cell_value))} 字符")
                        print(f"           内容: {str(cell_value)[:100]}...")
                wb_check.close()
            
            print(f"📊 Excel 文件生成完成！")
            
        except Exception as e:
            print(f"  ⚠️  生成 Excel 失败: {e}")
            import traceback
            traceback.print_exc()
    
    
    def get_summary(self) -> Dict:
        """获取数据摘要（基于 Excel 数据）"""
        total_count = sum(len(rows) for rows in self.excel_data.values() if rows)
        # 减去重复的 all_materials 计数
        if 'all_materials' in self.excel_data:
            total_count = len(self.excel_data['all_materials'])
        
        return {
            'text2video_count': 0,  # 已不再单独统计
            'image2video_count': 0,  # 已不再单独统计
            'total_count': total_count
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

