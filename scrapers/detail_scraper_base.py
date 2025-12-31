"""
详情页爬虫基类
点击作品卡片 -> 进入详情页 -> 提取完整信息
"""
from .base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import uuid
import os


class DetailScraperBase(BaseScraper):
    """详情页爬虫基类"""
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager, use_selenium=True)
        self.target_count = target_count
        self.wait = None  # WebDriverWait对象，在初始化driver后设置
    
    def _init_wait(self):
        """初始化WebDriverWait"""
        if self.driver and not self.wait:
            self.wait = WebDriverWait(self.driver, 10)
    
    def _scroll_and_load(self, scroll_times: int = 5):
        """滚动页面加载更多内容"""
        print(f"  🔄 滚动加载内容...")
        for i in range(scroll_times):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
    
    def _find_work_cards(self) -> list:
        """
        查找作品卡片元素
        子类需要实现此方法
        
        Returns:
            作品卡片元素列表
        """
        raise NotImplementedError("子类必须实现 _find_work_cards 方法")
    
    def _click_and_wait(self, element, wait_selector: str = None):
        """
        点击元素并等待新页面/模态框加载
        
        Args:
            element: 要点击的元素
            wait_selector: 等待出现的选择器（可选）
        """
        try:
            # 滚动到元素可见
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
            time.sleep(1)
            
            # 方法1: 使用JavaScript点击（绕过遮挡）
            try:
                self.driver.execute_script("arguments[0].click();", element)
                time.sleep(2)
                return True
            except Exception as e1:
                print(f"    ⚠️  JS点击失败，尝试普通点击")
            
            # 方法2: 查找并点击子元素（img/video）
            try:
                # 尝试找到内部的可点击元素
                clickable = element.find_elements(By.CSS_SELECTOR, 'img, video, a')
                if clickable:
                    self.driver.execute_script("arguments[0].click();", clickable[0])
                    time.sleep(2)
                    return True
            except:
                pass
            
            # 方法3: ActionChains点击
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.move_to_element(element).click().perform()
                time.sleep(2)
                return True
            except:
                pass
            
            # 方法4: 普通点击
            try:
                element.click()
                time.sleep(2)
                return True
            except:
                pass
            
            return False
            
        except Exception as e:
            print(f"    ⚠️  所有点击方法都失败")
            return False
    
    def _extract_detail_info(self) -> dict:
        """
        从详情页提取信息
        子类需要实现此方法
        
        Returns:
            {
                'prompt': str,           # 提示词
                'video_url': str,        # 视频URL
                'image_url': str,        # 图片URL
                'source_image_url': str, # 原图URL（图生视频）
                'type': str,            # 'text2video' 或 'image2video'
            }
        """
        raise NotImplementedError("子类必须实现 _extract_detail_info 方法")
    
    def _close_detail_page(self):
        """
        关闭详情页/模态框
        子类需要实现此方法
        """
        raise NotImplementedError("子类必须实现 _close_detail_page 方法")
    
    def _process_work(self, card_element, index: int, category: str) -> bool:
        """
        处理单个作品：点击 -> 提取 -> 下载 -> 上传S3
        
        Args:
            card_element: 作品卡片元素
            index: 索引
            category: 分类名称
            
        Returns:
            是否处理成功
        """
        try:
            print(f"\n  [{index}/{self.target_count}] 处理作品...")
            
            # 点击进入详情页
            if not self._click_and_wait(card_element):
                print(f"    ⚠️  无法打开详情页")
                return False
            
            # 提取详情信息（快速失败）
            detail_info = self._extract_detail_info()
            if not detail_info:
                print(f"    ⚠️  提取失败，跳过")
                self._close_detail_page()
                return False
            
            # 显示提示词（截断）
            prompt_text = detail_info.get('prompt', 'N/A')
            if len(prompt_text) > 100:
                prompt_display = prompt_text[:100] + '...'
            else:
                prompt_display = prompt_text
            print(f"    📝 提示词: {prompt_display}")
            
            # 生成ID和目录
            work_id = str(uuid.uuid4())[:8]
            work_type = detail_info.get('type', 'text2video')
            
            if work_type == 'image2video':
                save_dir = self.data_manager.image2video_dir / category.lower().replace(' ', '_')
            else:
                save_dir = self.data_manager.text2video_dir / category.lower().replace(' ', '_')
            
            save_dir.mkdir(exist_ok=True, parents=True)
            
            # 下载并上传文件（快速失败，实时写入）
            video_s3_url = None
            cover_s3_url = None
            source_s3_url = None
            
            # 下载原图（如果有）
            if detail_info.get('original_image_url'):
                try:
                    local_path = self._download_media(
                        detail_info['original_image_url'],
                        str(save_dir),
                        f"{work_id}_source",
                        referer=self.driver.current_url
                    )
                    if local_path:
                        filename = os.path.basename(local_path)
                        s3_url = self.data_manager.upload_to_s3(local_path, '', filename)
                        if s3_url:
                            source_s3_url = s3_url
                            print(f"    ✅ 原图: {s3_url}")
                except Exception as e:
                    print(f"    ⚠️  原图失败: {e}")
            
            # 下载视频
            if detail_info.get('video_url'):
                try:
                    local_path = self._download_media(
                        detail_info['video_url'],
                        str(save_dir),
                        f"{work_id}_video",
                        referer=self.driver.current_url
                    )
                    if local_path:
                        filename = os.path.basename(local_path)
                        s3_url = self.data_manager.upload_to_s3(local_path, '', filename)
                        if s3_url:
                            video_s3_url = s3_url
                            print(f"    ✅ 视频: {s3_url}")
                except Exception as e:
                    print(f"    ⚠️  视频失败: {e}")
            
            # 下载缩略图
            if detail_info.get('cover_url'):
                try:
                    local_path = self._download_media(
                        detail_info['cover_url'],
                        str(save_dir),
                        f"{work_id}_cover",
                        referer=self.driver.current_url
                    )
                    if local_path:
                        filename = os.path.basename(local_path)
                        s3_url = self.data_manager.upload_to_s3(local_path, '', filename)
                        if s3_url:
                            cover_s3_url = s3_url
                            print(f"    ✅ 封面: {s3_url}")
                except Exception as e:
                    print(f"    ⚠️  封面失败: {e}")
            
            # 写入TXT（固定4列：作品URL 原图URL 提示词 缩略图URL）
            if video_s3_url:
                prompt = detail_info.get('prompt', '')
                self.data_manager.append_to_txt(
                    work_url=video_s3_url,
                    site_name=category,
                    source_url=source_s3_url or '',
                    prompt=prompt,
                    cover_url=cover_s3_url or ''
                )
            
            # 关闭详情页
            self._close_detail_page()
            
            # 至少有视频就算成功
            if video_s3_url:
                file_count = sum([1 for x in [video_s3_url, cover_s3_url, source_s3_url] if x])
                print(f"    ✅ 完成 ({file_count} 个文件)")
                return True
            else:
                print(f"    ⚠️  视频下载失败")
                return False
            
        except Exception as e:
            print(f"    ❌ 失败，跳过: {str(e)[:50]}")
            # 快速失败，不打印详细错误
            try:
                self._close_detail_page()
            except:
                pass
            return False
    
    def scrape(self) -> int:
        """
        执行爬取 - 通用流程
        
        Returns:
            爬取数量
        """
        count = 0
        processed_indices = set()  # 记录已处理的索引
        
        try:
            self._init_wait()
            
            # 滚动加载内容
            self._scroll_and_load()
            
            # 处理每个作品（每次重新查找元素）
            for i in range(self.target_count):
                try:
                    # 每次都重新查找作品卡片（避免stale element）
                    print(f"  🔍 重新查找作品卡片...")
                    cards = self._find_work_cards()
                    
                    if len(cards) == 0:
                        print(f"  ⚠️  未找到作品卡片")
                        break
                    
                    print(f"  ✓ 找到 {len(cards)} 个作品")
                    
                    # 找一个还没处理过的卡片
                    card_to_process = None
                    card_index = None
                    
                    for idx, card in enumerate(cards):
                        if idx not in processed_indices:
                            card_to_process = card
                            card_index = idx
                            processed_indices.add(idx)
                            break
                    
                    if not card_to_process:
                        print(f"  ⚠️  所有卡片都已处理")
                        break
                    
                    # 处理这个作品
                    if self._process_work(card_to_process, count + 1, self.category_name):
                        count += 1
                    
                    # 避免请求过快
                    time.sleep(2)
                    
                    # 如果达到目标数量，提前退出
                    if count >= self.target_count:
                        break
                        
                except Exception as e:
                    print(f"  ⚠️  第 {i+1} 个作品处理失败: {str(e)[:50]}")
                    continue
            
            return count
            
        except Exception as e:
            print(f"  ✗ 爬取失败: {e}")
            import traceback
            traceback.print_exc()
            return count

