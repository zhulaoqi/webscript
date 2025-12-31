"""
Wan Video API 爬虫 - 纯 HTTP 请求方式
不依赖浏览器，直接调用后端 API
"""
import requests
import time
import uuid
import os
from typing import Dict, List, Optional
from .base_scraper import BaseScraper
from utils import DownloadUtils


class WanVideoAPIScraper(BaseScraper):
    """
    Wan Video API 爬虫
    
    使用步骤：
    1. 手动打开 Chrome → F12 → Network 标签
    2. 访问 https://create.wan.video/
    3. 点击作品，观察 Network 中的 API 请求
    4. 找到返回视频数据的 API，复制 URL 和 Headers
    5. 填写到下面的配置中
    """
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager, use_selenium=False)
        self.target_count = target_count
        self.category_name = 'WanVideo'  # 去掉空格
        
        # ========== 需要手动配置的部分 ==========
        # TODO: 从 Chrome DevTools 复制真实的 API 地址
        self.api_base_url = 'https://api.wan.video'  # 需要替换为真实的
        
        # TODO: 从 Chrome DevTools 复制真实的 Headers
        self.headers = {
            'User-Agent': DownloadUtils.get_random_user_agent(),
            'Accept': 'application/json',
            'Referer': 'https://create.wan.video/',
            # 'Authorization': 'Bearer xxx',  # 如果需要认证，从浏览器复制
            # 'Cookie': 'session=xxx; user_id=xxx',  # 如果需要 Cookie
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        if self.proxies:
            self.session.proxies.update(self.proxies)
    
    def scrape(self) -> int:
        """执行爬取 - API 方式"""
        print(f"\n开始爬取 Wan Video (目标: {self.target_count} 条)")
        print("=" * 60)
        print("⚠️  当前使用 API 方式，需要先手动配置 API 地址！")
        print("=" * 60)
        
        count = 0
        
        try:
            # 第一步：获取作品列表
            videos = self._fetch_video_list()
            
            if not videos:
                print("❌ 未获取到作品列表，请检查 API 配置")
                return 0
            
            print(f"✅ 获取到 {len(videos)} 个作品\n")
            
            # 第二步：逐个处理
            for i, video in enumerate(videos[:self.target_count], 1):
                print(f"[{i}/{self.target_count}] 处理作品...")
                
                try:
                    # 获取详情（如果列表数据不完整）
                    detail_info = self._fetch_video_detail(video)
                    
                    if detail_info and detail_info.get('video_url'):
                        if self._download_and_upload(detail_info, i):
                            count += 1
                            print(f"  ✅ 成功 (总计: {count})\n")
                    else:
                        print(f"  ⚠️  数据不完整\n")
                    
                    # 礼貌延迟
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"  ❌ 失败: {str(e)}\n")
            
            print(f"\n✓ Wan Video 完成: {count} 条")
            return count
            
        except Exception as e:
            print(f"✗ 失败: {e}")
            import traceback
            traceback.print_exc()
            return count
    
    def _fetch_video_list(self) -> List[Dict]:
        """
        获取作品列表
        
        TODO: 需要根据真实 API 修改
        可能的 API 格式：
        - GET /api/v1/explore/videos?page=1&limit=50
        - POST /api/videos/list
        """
        print("📡 获取作品列表...")
        
        # 示例代码（需要根据真实 API 修改）
        try:
            # 方式 1: GET 请求
            response = self.session.get(
                f"{self.api_base_url}/api/v1/explore/videos",
                params={
                    'page': 1,
                    'limit': self.target_count,
                    'category': 'all'  # 或 'image2video', 'text2video'
                },
                timeout=30
            )
            
            # 方式 2: POST 请求（如果是 POST）
            # response = self.session.post(
            #     f"{self.api_base_url}/api/videos/list",
            #     json={
            #         'page': 1,
            #         'pageSize': self.target_count
            #     },
            #     timeout=30
            # )
            
            response.raise_for_status()
            data = response.json()
            
            # 解析响应（需要根据真实响应格式修改）
            # 可能的格式：
            # - data['data']['videos']
            # - data['videos']
            # - data['items']
            
            if 'data' in data and 'videos' in data['data']:
                return data['data']['videos']
            elif 'videos' in data:
                return data['videos']
            else:
                print(f"⚠️  未知的响应格式: {list(data.keys())}")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"❌ API 请求失败: {e}")
            print(f"   URL: {self.api_base_url}")
            print(f"   提示: 请打开浏览器 F12 → Network，找到真实的 API 地址")
            return []
    
    def _fetch_video_detail(self, video: Dict) -> Optional[Dict]:
        """
        获取作品详情（如果列表数据不完整）
        
        参数:
            video: 列表中的作品信息
        
        返回:
            包含完整信息的字典
        """
        # 如果列表数据已经完整，直接返回
        if all(k in video for k in ['video_url', 'prompt']):
            return self._normalize_video_data(video)
        
        # 否则，调用详情 API
        try:
            video_id = video.get('id') or video.get('video_id')
            if not video_id:
                return self._normalize_video_data(video)
            
            response = self.session.get(
                f"{self.api_base_url}/api/v1/videos/{video_id}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            # 解析详情
            detail = data.get('data') or data
            return self._normalize_video_data(detail)
            
        except Exception as e:
            print(f"  ⚠️  获取详情失败: {e}")
            return self._normalize_video_data(video)
    
    def _normalize_video_data(self, data: Dict) -> Dict:
        """
        标准化数据格式
        
        TODO: 根据真实 API 响应字段名调整映射关系
        """
        # 可能的字段名变体
        video_url_keys = ['video_url', 'videoUrl', 'url', 'video', 'media_url']
        cover_url_keys = ['cover_url', 'coverUrl', 'cover', 'thumbnail', 'poster']
        prompt_keys = ['prompt', 'description', 'text', 'caption']
        source_keys = ['source_image_url', 'sourceImageUrl', 'source', 'input_image']
        
        def get_first_value(data: Dict, keys: List[str]) -> Optional[str]:
            for key in keys:
                if key in data and data[key]:
                    return data[key]
            return None
        
        result = {
            'video_url': get_first_value(data, video_url_keys),
            'cover_url': get_first_value(data, cover_url_keys),
            'prompt': get_first_value(data, prompt_keys) or 'No prompt',
            'original_image_url': get_first_value(data, source_keys),
            'type': 'image2video' if get_first_value(data, source_keys) else 'text2video',
        }
        
        return result
    
    def _download_and_upload(self, detail_info: dict, index: int) -> bool:
        """下载并上传"""
        try:
            work_id = str(uuid.uuid4())[:8]
            work_type = detail_info.get('type', 'text2video')
            
            if work_type == 'image2video':
                save_dir = self.data_manager.image2video_dir / 'wan_video'
            else:
                save_dir = self.data_manager.text2video_dir / 'wan_video'
            
            save_dir.mkdir(exist_ok=True, parents=True)
            
            video_s3_url = None
            cover_s3_url = None
            source_s3_url = None
            
            # 下载原图
            if detail_info.get('original_image_url'):
                try:
                    local_path = self._download_media(
                        detail_info['original_image_url'],
                        str(save_dir),
                        f"{work_id}_source"
                    )
                    if local_path:
                        s3_url = self.data_manager.upload_to_s3(
                            local_path, '', os.path.basename(local_path))
                        if s3_url:
                            source_s3_url = s3_url
                except:
                    pass
            
            # 下载视频
            if detail_info.get('video_url'):
                try:
                    local_path = self._download_media(
                        detail_info['video_url'],
                        str(save_dir),
                        f"{work_id}_video"
                    )
                    if local_path:
                        s3_url = self.data_manager.upload_to_s3(
                            local_path, '', os.path.basename(local_path))
                        if s3_url:
                            video_s3_url = s3_url
                except:
                    pass
            
            # 下载封面
            if detail_info.get('cover_url'):
                try:
                    local_path = self._download_media(
                        detail_info['cover_url'],
                        str(save_dir),
                        f"{work_id}_cover"
                    )
                    if local_path:
                        s3_url = self.data_manager.upload_to_s3(
                            local_path, '', os.path.basename(local_path))
                        if s3_url:
                            cover_s3_url = s3_url
                except:
                    pass
            
            # 写入 TXT
            if video_s3_url:
                self.data_manager.append_to_txt(
                    work_url=video_s3_url,
                    site_name=self.category_name,
                    source_url=source_s3_url or '',
                    prompt=detail_info.get('prompt', ''),
                    cover_url=cover_s3_url or ''
                )
                return True
            
            return False
            
        except Exception as e:
            print(f"  ❌ 下载上传失败: {e}")
            return False

