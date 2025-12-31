"""
Higgsfield.ai 详情页爬虫
"""
from .detail_scraper_base import DetailScraperBase
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time


class HiggsfieldDetailScraper(DetailScraperBase):
    """Higgsfield 详情页爬虫"""
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager, target_count)
        self.base_url = 'https://higgsfield.ai/'
        self.category_name = 'Higgsfield'
    
    def scrape(self) -> int:
        """执行爬取"""
        print(f"\n开始爬取 Higgsfield.ai (目标: {self.target_count} 条)")
        
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
            # 优先找图片/视频，避免被遮挡
            selectors = [
                'img[src*="higgsfield"]',
                'video',
                'div[class*="video"] img',
                'div[class*="card"] img',
                'article img',
                'a[href*="video"]',
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    valid = []
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.size['width'] > 100 and elem.size['height'] > 100:
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
        """从详情页提取信息 - Higgsfield专用"""
        try:
            time.sleep(3)
            
            # 提示词提取（Higgsfield多种方式，宽松策略）
            prompt = ''
            
            # 方法1: textarea和input（最直接）
            try:
                inputs = self.driver.find_elements(By.XPATH, "//textarea | //input[@type='text']")
                for inp in inputs:
                    text = inp.get_attribute('value') or inp.text
                    if text and len(text) > 10:
                        prompt = text.strip()
                        print(f"    ✓ 找到提示词（input/textarea）: {prompt[:60]}...")
                        break
            except:
                pass
            
            # 方法2: prompt相关的class
            if not prompt:
                try:
                    prompt_containers = self.driver.find_elements(By.XPATH, 
                        "//*[contains(@class, 'prompt') or contains(@class, 'caption') or contains(@class, 'description')]")
                    for container in prompt_containers[:10]:
                        text = container.text.strip()
                        if text and 15 < len(text) < 800:
                            prompt = text
                            print(f"    ✓ 找到提示词（prompt容器）: {prompt[:60]}...")
                            break
                except:
                    pass
            
            # 方法3: 任何包含描述性词汇的文本
            if not prompt:
                try:
                    text_elements = self.driver.find_elements(By.XPATH, 
                        "//p[string-length(normalize-space(.)) > 20] | //span[string-length(normalize-space(.)) > 20]")
                    for elem in text_elements[:30]:
                        text = elem.text.strip()
                        if text and 20 < len(text) < 500:
                            # 只排除明显的按钮
                            if not any(btn in text.lower() for btn in ['click here', 'sign in', 'log in', 'button']):
                                prompt = text
                                print(f"    ✓ 找到提示词（文本元素）: {prompt[:60]}...")
                                break
                except:
                    pass
            
            # 查找原图（图生视频的输入图）- 使用严格过滤
            original_image_url = None
            try:
                candidates = []
                # 查找标记为input、reference、source等的图片
                for keyword in ['input', 'reference', 'source', 'original']:
                    try:
                        labels = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}') or contains(@class, '{keyword}')]")
                        for label in labels:
                            parent = label.find_element(By.XPATH, "../..")
                            imgs = parent.find_elements(By.TAG_NAME, 'img')
                            for img in imgs:
                                try:
                                    src = img.get_attribute('src')
                                    if not src or 'higgsfield' not in src.lower():
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
                
                # 选择最大的
                if candidates:
                    candidates.sort(key=lambda x: x['area'], reverse=True)
                    best = candidates[0]
                    original_image_url = best['url']
                    print(f"    ✓ 找到原图（图生视频）[{best['width']}x{best['height']}]")
            except:
                pass
            
            # 判断类型
            work_type = 'image2video' if original_image_url else 'text2video'
            print(f"    ℹ️  识别类型: {work_type}")
            
            # 提取视频和封面
            video_url = None
            cover_url = None
            try:
                videos = self.driver.find_elements(By.TAG_NAME, 'video')
                for video in videos:
                    # 提取封面
                    poster = video.get_attribute('poster')
                    if poster and not cover_url:
                        cover_url = poster
                        print(f"    ✓ 找到视频封面")
                    
                    # 提取视频URL
                    src = video.get_attribute('src')
                    if not src:
                        try:
                            source = video.find_element(By.TAG_NAME, 'source')
                            src = source.get_attribute('src')
                        except:
                            pass
                    if src and src.startswith('http') and 'blob:' not in src:
                        video_url = src
                        print(f"    ✓ 找到视频URL")
                        break
            except:
                pass
            
            # 提取主图（作为封面备选）
            main_image_url = None
            if not cover_url:
                try:
                    imgs = self.driver.find_elements(By.TAG_NAME, 'img')
                    for img in imgs:
                        src = img.get_attribute('src')
                        if src and 'higgsfield' in src.lower():
                            skip = ['profile', 'avatar', 'logo', 'icon']
                            if not any(p in src.lower() for p in skip):
                                if img.size['width'] > 200 and img.size['height'] > 200:
                                    main_image_url = src
                                    print(f"    ✓ 找到主图（作为封面）")
                                    break
                except:
                    pass
            
            # 验证必要数据
            if not video_url:
                print(f"    ❌ 未找到视频URL")
                return None
            
            return {
                'prompt': prompt or 'No prompt available',
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

