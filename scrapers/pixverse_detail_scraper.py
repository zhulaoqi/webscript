"""
Pixverse.ai 详情页爬虫
"""
from .detail_scraper_base import DetailScraperBase
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


class PixverseDetailScraper(DetailScraperBase):
    """Pixverse 详情页爬虫"""
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager, target_count)
        self.base_url = 'https://app.pixverse.ai/onboard'
        self.category_name = 'Pixverse'
    
    def scrape(self) -> int:
        """执行爬取"""
        print(f"\n开始爬取 Pixverse.ai (目标: {self.target_count} 条)")
        
        try:
            print(f"  访问: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(5)
            
            return super().scrape()
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return 0
    
    def _find_work_cards(self) -> list:
        """查找作品卡片"""
        try:
            selectors = [
                'img[src*="pixverse"]',
                'video',
                'div[class*="video"] img',
                'div[class*="card"] img',
                'div[class*="content"] img',
                'article img',
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    valid = []
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.size['width'] > 100:
                                if elem.tag_name == 'img':
                                    src = elem.get_attribute('src') or ''
                                    skip = ['logo', 'avatar', 'icon', 'profile']
                                    if any(s in src.lower() for s in skip):
                                        continue
                                valid.append(elem)
                        except:
                            continue
                    
                    if len(valid) > 5:
                        print(f"    ✓ 使用选择器: {selector}, 找到 {len(valid)} 个")
                        return valid
                except:
                    continue
            
            return []
            
        except Exception as e:
            print(f"    ❌ 查找卡片失败: {e}")
            return []
    
    def _extract_detail_info(self) -> dict:
        """从详情页提取信息 - Pixverse专用"""
        try:
            time.sleep(3)
            
            # 提示词提取（Pixverse专用，宽松策略）
            prompt = ''
            
            # 方法1: textarea和input
            try:
                inputs = self.driver.find_elements(By.XPATH, "//textarea | //input[@type='text']")
                for inp in inputs:
                    text = inp.get_attribute('value') or inp.text
                    if text and len(text) > 10:
                        prompt = text.strip()
                        print(f"    ✓ 找到提示词（input）: {prompt[:60]}...")
                        break
            except:
                pass
            
            # 方法2: prompt/detail/description相关class
            if not prompt:
                try:
                    containers = self.driver.find_elements(By.XPATH, 
                        "//*[contains(@class, 'prompt') or contains(@class, 'detail') or contains(@class, 'description')]")
                    for container in containers[:10]:
                        text = container.text.strip()
                        if text and 15 < len(text) < 800:
                            prompt = text
                            print(f"    ✓ 找到提示词（容器）: {prompt[:60]}...")
                            break
                except:
                    pass
            
            # 方法3: 任何合适的文本
            if not prompt:
                try:
                    texts = self.driver.find_elements(By.XPATH, "//p | //span")
                    for elem in texts[:50]:
                        text = elem.text.strip()
                        if text and 20 < len(text) < 500:
                            if not any(btn in text.lower() for btn in ['sign in', 'log in', 'click', 'button']):
                                prompt = text
                                print(f"    ✓ 找到提示词（文本）: {prompt[:60]}...")
                                break
                except:
                    pass
            
            # 查找原图 - 使用严格过滤
            original_image_url = None
            try:
                candidates = []
                for keyword in ['input', 'reference', 'source']:
                    labels = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    for label in labels[:3]:
                        try:
                            parent = label.find_element(By.XPATH, "../..")
                            imgs = parent.find_elements(By.TAG_NAME, 'img')
                            for img in imgs[:5]:
                                try:
                                    src = img.get_attribute('src')
                                    if not src or 'pixverse' not in src.lower():
                                        continue
                                    
                                    # 排除UI元素
                                    exclude_keywords = [
                                        'profile', 'avatar', 'logo', 'icon', 'favicon',
                                        'price', 'pricing', 'banner', 'ad', 'button',
                                        'nav', 'menu', 'badge', 'tag', 'coin', 'credit'
                                    ]
                                    if any(kw in src.lower() for kw in exclude_keywords):
                                        continue
                                    
                                    # 检查尺寸
                                    width = img.size.get('width', 0)
                                    height = img.size.get('height', 0)
                                    if width < 400 or height < 400:
                                        continue
                                    
                                    area = width * height
                                    candidates.append({'url': src, 'area': area, 'width': width, 'height': height})
                                except:
                                    continue
                        except:
                            continue
                    if candidates:
                        break
                
                if candidates:
                    candidates.sort(key=lambda x: x['area'], reverse=True)
                    best = candidates[0]
                    original_image_url = best['url']
                    print(f"    ✓ 找到原图 [{best['width']}x{best['height']}]")
            except:
                pass
            
            work_type = 'image2video' if original_image_url else 'text2video'
            print(f"    ℹ️  类型: {work_type}")
            
            # 提取视频
            video_url = None
            cover_url = None
            try:
                videos = self.driver.find_elements(By.TAG_NAME, 'video')
                for video in videos:
                    poster = video.get_attribute('poster')
                    if poster:
                        cover_url = poster
                    
                    src = video.get_attribute('src')
                    if not src:
                        try:
                            source = video.find_element(By.TAG_NAME, 'source')
                            src = source.get_attribute('src')
                        except:
                            pass
                    if src and src.startswith('http') and 'blob:' not in src:
                        video_url = src
                        print(f"    ✓ 找到视频")
                        break
            except:
                pass
            
            # 提取主图
            main_image_url = None
            if not cover_url:
                try:
                    imgs = self.driver.find_elements(By.TAG_NAME, 'img')
                    for img in imgs:
                        src = img.get_attribute('src')
                        if src and 'pixverse' in src.lower():
                            skip = ['profile', 'avatar', 'logo', 'icon']
                            if not any(p in src.lower() for p in skip):
                                if img.size.get('width', 0) > 200:
                                    main_image_url = src
                                    break
                except:
                    pass
            
            if not video_url:
                print(f"    ❌ 未找到视频")
                return None
            
            return {
                'prompt': prompt or 'No prompt',
                'video_url': video_url,
                'cover_url': cover_url or main_image_url,
                'original_image_url': original_image_url,
                'type': work_type,
            }
            
        except Exception as e:
            print(f"    ❌ 提取失败: {e}")
            return None
    
    def _close_detail_page(self):
        """关闭详情页"""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(1)
        except:
            try:
                self.driver.back()
                time.sleep(1)
            except:
                pass

