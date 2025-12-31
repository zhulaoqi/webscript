"""
Higgsfield.ai 网站爬虫 - 简化版
直接抓取页面上的所有图片和视频
"""
from typing import List, Dict
from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
import time
import uuid
import os


class HiggsfieldScraper(BaseScraper):
    """Higgsfield 爬虫"""
    
    def __init__(self, data_manager, target_count_per_category: int = 50):
        super().__init__(data_manager, use_selenium=True)
        self.target_count = target_count_per_category  # 现在表示总数，不是每个分类的数量
        self.base_url = 'https://higgsfield.ai/'
        self.categories = [
            'Kling 2.5 Turbo',
            'Camera Controls',
            'Viral',
            'Commercial',
            'UGC',
            'Sora 2 Community',
            'Wan 2.5 Community'
        ]
    
    def scrape(self) -> int:
        """执行爬取 - 简化版"""
        print(f"\n开始爬取 Higgsfield.ai (目标: {self.target_count} 条)")
        
        total_count = 0
        
        try:
            print(f"  访问: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(5)
            
            # 滚动加载
            print("  滚动加载...")
            for i in range(5):
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            # 直接获取所有媒体
            print("  提取媒体...")
            all_imgs = self.driver.find_elements(By.TAG_NAME, 'img')
            all_videos = self.driver.find_elements(By.TAG_NAME, 'video')
            
            print(f"  找到 {len(all_imgs)} 张图片, {len(all_videos)} 个视频")
            
            # 提取URL
            urls = []
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
                            urls.append(src)
                except:
                    pass
            
            for video in all_videos:
                try:
                    src = video.get_attribute('src')
                    if not src:
                        try:
                            source = video.find_element(By.TAG_NAME, 'source')
                            src = source.get_attribute('src')
                        except:
                            pass
                    if src and src.startswith('http'):
                        urls.append(src)
                except:
                    pass
            
            print(f"  提取到 {len(urls)} 个有效URL")
            
            # 处理
            target = self.target_count  # 直接使用target_count，不再乘以分类数
            for url in urls[:target]:
                try:
                    video_id = str(uuid.uuid4())[:8]
                    save_dir = self.data_manager.text2video_dir / 'higgsfield'
                    save_dir.mkdir(exist_ok=True, parents=True)
                    
                    local_path = self._download_media(url, str(save_dir), video_id, referer=self.base_url)
                    if not local_path:
                        continue
                    
                    filename = os.path.basename(local_path)
                    s3_url = self.data_manager.upload_to_s3(local_path, '', filename)
                    
                    if s3_url:
                        record = {
                            'id': video_id,
                            'category': 'Higgsfield',
                            'prompt': 'from higgsfield.ai',
                            'video_s3_url': s3_url if url.endswith('.mp4') else '',
                            'thumbnail_s3_url': s3_url if not url.endswith('.mp4') else '',
                        }
                        self.data_manager.add_text2video(record)
                        total_count += 1
                        print(f"  ✓ {total_count}/{target}")
                
                except Exception as e:
                    continue
            
            return total_count
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return total_count
    

