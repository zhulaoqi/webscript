"""
Imagine.art 详情页爬虫
点击作品 -> 获取提示词和媒体文件
"""
from .detail_scraper_base import DetailScraperBase
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


class ImagineArtDetailScraper(DetailScraperBase):
    """Imagine.art 详情页爬虫"""
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager, target_count)
        self.base_url = 'https://www.imagine.art/community'
        self.category_name = 'ImagineArt'  # 去掉点号
    
    def scrape(self) -> int:
        """执行爬取"""
        print(f"\n开始爬取 Imagine.art (目标: {self.target_count} 条)")
        
        try:
            print(f"  访问: {self.base_url}")
            self.driver.get(self.base_url)
            time.sleep(5)
            
            # 调用父类的通用爬取流程
            return super().scrape()
            
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            return 0
    
    def _find_work_cards(self) -> list:
        """查找作品卡片"""
        try:
            # 直接找图片，避免被遮挡
            selectors = [
                'img[src*="imagine.art"]',
                'img[src*="cdn"]',
                'button img',
                'div[class*="card"] img',
                'article img',
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    valid = []
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.size['width'] > 100:
                                src = elem.get_attribute('src') or ''
                                skip = ['logo', 'avatar', 'icon', 'profile', 'community heading']
                                if any(s in src.lower() for s in skip):
                                    continue
                                valid.append(elem)
                        except:
                            continue
                    
                    if len(valid) > 10:
                        print(f"    ✓ 使用选择器: {selector}, 找到 {len(valid)} 个")
                        return valid
                except:
                    continue
            
            return []
            
        except Exception as e:
            print(f"    ❌ 查找卡片失败: {e}")
            return []
    
    def _extract_detail_info(self) -> dict:
        """从详情页提取信息 - Imagine.art专用"""
        try:
            time.sleep(3)
            
            # 提示词提取（Imagine.art专用，宽松策略）
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
            
            # 方法2: prompt/caption/description相关class
            if not prompt:
                try:
                    containers = self.driver.find_elements(By.XPATH, 
                        "//*[contains(@class, 'prompt') or contains(@class, 'caption') or contains(@class, 'description')]")
                    for div in containers[:10]:
                        text = div.text.strip()
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
            
            # 查找原图（图生视频）- 使用严格过滤
            original_image_url = None
            try:
                candidates = []
                for keyword in ['input', 'reference', 'source', 'original']:
                    labels = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                    for label in labels[:3]:
                        try:
                            parent = label.find_element(By.XPATH, "../..")
                            imgs = parent.find_elements(By.TAG_NAME, 'img')
                            for img in imgs[:5]:
                                try:
                                    src = img.get_attribute('src')
                                    if not src or 'imagine' not in src.lower():
                                        continue
                                    
                                    # 排除UI元素
                                    exclude_keywords = [
                                        'profile', 'avatar', 'logo', 'icon', 'favicon', 'user',
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
                    if poster and not cover_url:
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
                        if src and 'imagine' in src.lower():
                            skip = ['profile', 'avatar', 'logo', 'icon', 'user']
                            if not any(p in src.lower() for p in skip):
                                if img.size.get('width', 0) > 200:
                                    main_image_url = src
                                    print(f"    ✓ 找到主图")
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
            print(f"    ❌ 提取信息失败: {e}")
            return None
    
    def _close_detail_page(self):
        """关闭详情页"""
        try:
            # 方法1: 按ESC键
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                time.sleep(1)
                return
            except:
                pass
            
            # 方法2: 点击关闭按钮
            close_selectors = [
                'button[aria-label="Close"]',
                'button[class*="close"]',
                '[class*="close-button"]',
                'button:contains("×")',
            ]
            
            for selector in close_selectors:
                try:
                    close_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    close_btn.click()
                    time.sleep(1)
                    return
                except:
                    continue
            
            # 方法3: 后退
            self.driver.back()
            time.sleep(1)
            
        except Exception as e:
            print(f"    ⚠️  关闭详情页失败: {e}")

