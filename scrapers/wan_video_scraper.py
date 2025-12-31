"""
Wan Video 网站爬虫 - 简化版
直接抓取页面上的所有图片和视频
"""
from typing import List, Dict
from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
import time
import uuid
import os


class WanVideoScraper(BaseScraper):
    """Wan Video 爬虫 - 简化版"""
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager, use_selenium=True)
        self.target_count = target_count
        self.base_url = 'https://create.wan.video/'
    
    def scrape(self) -> int:
        """执行爬取 - 简化版：直接抓取所有图片和视频"""
        print(f"\n开始爬取 Wan Video (目标: {self.target_count} 条)")
        
        try:
            print(f"  访问: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(5)  # 等待页面加载
            
            # 滚动几次加载更多
            print("  滚动加载...")
            for i in range(3):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # 直接获取所有img和video标签
            print("  提取媒体URL...")
            all_imgs = self.driver.find_elements(By.TAG_NAME, 'img')
            all_videos = self.driver.find_elements(By.TAG_NAME, 'video')
            
            print(f"  找到 {len(all_imgs)} 张图片, {len(all_videos)} 个视频")
            
            # 提取URL
            urls = []
            
            # 提取图片URL
            for img in all_imgs:
                try:
                    src = img.get_attribute('src') or img.get_attribute('data-src')
                    if src and src.startswith('http'):
                        # 过滤掉非素材URL
                        skip_patterns = [
                            'favicon', 'logo', 'avatar', 'icon',
                            'profile-image', 'user-avatar', 'user_avatar',
                            '/users/', '/user/', '/profile/', '/creator/'
                        ]
                        if not any(x in src.lower() for x in skip_patterns):
                            urls.append(('image', src))
                except:
                    pass
            
            # 提取视频URL
            for video in all_videos:
                try:
                    src = video.get_attribute('src')
                    if not src:
                        source = video.find_element(By.TAG_NAME, 'source')
                        src = source.get_attribute('src')
                    if src and src.startswith('http'):
                        urls.append(('video', src))
                except:
                    pass
            
            print(f"  提取到 {len(urls)} 个有效URL")
            
            # 处理前target_count个
            count = 0
            for idx, (media_type, url) in enumerate(urls[:self.target_count], 1):
                try:
                    print(f"\n  [{idx}/{self.target_count}] 处理: {url[:60]}...")
                    
                    video_id = str(uuid.uuid4())[:8]
                    save_dir = self.data_manager.text2video_dir / 'wan_video'
                    save_dir.mkdir(exist_ok=True, parents=True)
                    
                    # 下载（传递正确的referer）
                    print(f"    📥 下载中...")
                    local_path = self._download_media(url, str(save_dir), video_id, referer=self.base_url)
                    if not local_path:
                        print(f"    ⚠️  下载失败，跳过")
                        continue
                    
                    print(f"    ✓ 下载成功: {local_path}")
                    
                    # 上传S3
                    filename = os.path.basename(local_path)
                    s3_url = self.data_manager.upload_to_s3(local_path, '', filename)
                    
                    # 保存记录
                    if s3_url:
                        record = {
                            'id': video_id,
                            'category': 'Wan Video',
                            'prompt': f'{media_type} from wan.video',
                            'video_s3_url': s3_url if media_type == 'video' else '',
                            'thumbnail_s3_url': s3_url if media_type == 'image' else '',
                        }
                        self.data_manager.add_text2video(record)
                        count += 1
                        print(f"    ✅ 完成 ({count}/{self.target_count})")
                    else:
                        print(f"    ⚠️  S3上传失败，未保存数据")
                
                except Exception as e:
                    print(f"    ❌ 错误: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            return count
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return 0
    

