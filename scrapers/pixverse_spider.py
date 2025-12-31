"""
Pixverse Spider - 基于 Scrapy 框架
专业爬虫实现，直接调用 API
"""
import scrapy
from scrapy.http import Request
import json
import os
from pathlib import Path
from typing import Dict, Optional
import requests
from scrapy.exceptions import CloseSpider


class PixverseSpider(scrapy.Spider):
    name = 'pixverse'
    
    # API 配置
    api_url = 'https://app-api.pixverse.ai/creative_platform/content/relation/list'
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US',
        'ai-anonymous-id': '19b725a3e4c4a4-02a033b10ed1b76-1c525631-3686400-19b725a3e4d1da3',
        'origin': 'https://app.pixverse.ai',
        'referer': 'https://app.pixverse.ai/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'x-platform': 'Web',
    }
    
    # 类别映射（需要找到对应的 secondary_category ID）
    categories = {
        'Winter Vibe': 113,
        'Ad Magic': 114,
        'Cinematic Narrative': 115,
        'Stylistic Art': 116,
        'Animal Theatre': 117,
        'Effects Rendering': 118,
        'Emotional Close-up': 119,
    }
    
    def __init__(self, target_count=20, data_manager=None, categories=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_count_per_category = int(target_count)
        self.data_manager = data_manager
        self.category_name = 'Pixverse'
        self.scraped_count = 0
        self.total_target = 0
        
        # 如果指定了类别，则只爬取这些类别
        if categories:
            self.categories = {k: v for k, v in self.categories.items() if k in categories}
        
        # 每个类别的计数器
        self.category_counts = {cat: 0 for cat in self.categories.keys()}
        self.total_target = len(self.categories) * self.target_count_per_category
        
        # 确保有 data_manager
        if not self.data_manager:
            self.logger.error("❌ data_manager 未提供！")
            raise ValueError("data_manager is required")
    
    def start_requests(self):
        """开始请求所有类别"""
        for category_name, category_id in self.categories.items():
            self.logger.info(f"\n📂 开始爬取类别: {category_name}")
            yield self._make_request(category_name, category_id, offset=0)
    
    def _make_request(self, category_name, category_id, offset):
        """构造 API 请求"""
        params = {
            'offset': offset,
            'limit': 50,
            'primary_category': 1,
            'secondary_category': category_id,
            'platform': 'web',
            'web_offset': offset,
            'app_offset': 0,
        }
        
        url = self.api_url + '?' + '&'.join([f"{k}={v}" for k, v in params.items()])
        
        return scrapy.Request(
            url=url,
            headers=self.headers,
            callback=self.parse_api,
            errback=self.errback_httpbin,
            dont_filter=True,
            meta={
                'category_name': category_name,
                'category_id': category_id,
                'offset': offset
            }
        )
    
    def parse_api(self, response):
        """解析 API 响应"""
        try:
            data = json.loads(response.text)
            category_name = response.meta['category_name']
            category_id = response.meta['category_id']
            offset = response.meta['offset']
            
            if data.get('ErrCode') != 0:
                self.logger.error(f"❌ API 返回错误: {data.get('ErrMsg', '未知错误')}")
                return
            
            resp = data.get('Resp', {})
            items = resp.get('data', [])
            total = resp.get('total', 0)
            
            self.logger.info(f"✅ [{category_name}] 找到 {len(items)} 个作品 (总共 {total})")
            
            # 处理每个作品
            for item_data in items:
                # 检查当前类别是否已达到目标
                if self.category_counts[category_name] >= self.target_count_per_category:
                    break
                
                # 检查总数是否已达到目标
                if self.scraped_count >= self.total_target:
                    raise CloseSpider('Target count reached')
                
                item = self._extract_work_data(item_data, category_name)
                if item:
                    self.category_counts[category_name] += 1
                    self.scraped_count += 1
                    self._process_work(item)
                    self.logger.info(
                        f"   ✅ [{category_name}] {self.category_counts[category_name]}/{self.target_count_per_category} "
                        f"(总计: {self.scraped_count}/{self.total_target})"
                    )
            
            # 自动翻页（如果当前类别还没达到目标）
            if self.category_counts[category_name] < self.target_count_per_category:
                next_offset = offset + 50
                if next_offset < total:
                    self.logger.info(f"   ⏩ [{category_name}] 翻页到 offset={next_offset}...")
                    yield self._make_request(category_name, category_id, next_offset)
                else:
                    self.logger.info(f"   ℹ️  [{category_name}] 已到最后一页")
        
        except CloseSpider as e:
            self.logger.info(f"🏁 爬取完成: {e}")
            raise
        except json.JSONDecodeError:
            self.logger.warning(f"⚠️  API 响应不是 JSON: {response.url}")
        except Exception as e:
            self.logger.error(f"❌ 解析 API 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_work_data(self, item_data, category_name):
        """提取作品数据"""
        try:
            # 判断类型
            create_mode = item_data.get('create_mode', '')
            work_type = 'text2video'
            source_image_url = ''
            
            if create_mode in ['image_text', 'image']:
                work_type = 'image2video'
                # 提取原图
                source_image_url = (
                    item_data.get('customer_img_url') or 
                    item_data.get('img_url') or 
                    item_data.get('first_frame', '')
                )
            
            video_url = item_data.get('url', '')
            cover_url = item_data.get('first_frame', '')
            prompt = item_data.get('prompt', '')
            
            return {
                'id': str(item_data.get('video_id', '')),
                'prompt': prompt,
                'video_url': video_url,
                'source_image_url': source_image_url,
                'cover_url': cover_url,
                'type': work_type,
                'category': category_name,
                'media_type': 'video',
            }
        
        except Exception as e:
            self.logger.error(f"提取作品数据失败: {e}")
            return None
    
    def _process_work(self, item):
        """处理作品：下载、上传、写入TXT"""
        try:
            work_id = item['id'][:8] if item.get('id') else str(self.scraped_count)
            work_type = item['type']
            category = item['category']
            
            # 确定保存目录
            if work_type == 'image2video':
                save_dir = self.data_manager.image2video_dir / self.category_name / category
            else:
                save_dir = self.data_manager.text2video_dir / self.category_name / category
            
            save_dir.mkdir(exist_ok=True, parents=True)
            
            video_s3_url = None
            cover_s3_url = None
            source_s3_url = None
            
            # 下载原图（如果有）
            if item.get('source_image_url'):
                try:
                    self.logger.info(f"    📥 下载原图...")
                    local_path = self._download_file(
                        item['source_image_url'],
                        save_dir / f"{work_id}_source.jpg"
                    )
                    if local_path:
                        s3_url = self.data_manager.upload_to_s3(
                            str(local_path), '', os.path.basename(str(local_path)))
                        if s3_url:
                            source_s3_url = s3_url
                            self.logger.info(f"    ✅ 原图上传成功")
                except Exception as e:
                    self.logger.warning(f"    ⚠️  原图处理失败: {e}")
            
            # 下载视频
            if item.get('video_url'):
                try:
                    self.logger.info(f"    📥 下载视频...")
                    local_path = self._download_file(
                        item['video_url'],
                        save_dir / f"{work_id}_video.mp4"
                    )
                    if local_path:
                        s3_url = self.data_manager.upload_to_s3(
                            str(local_path), '', os.path.basename(str(local_path)))
                        if s3_url:
                            video_s3_url = s3_url
                            self.logger.info(f"    ✅ 视频上传成功")
                except Exception as e:
                    self.logger.warning(f"    ⚠️  视频处理失败: {e}")
            
            # 下载封面
            if item.get('cover_url'):
                try:
                    self.logger.info(f"    📥 下载封面...")
                    local_path = self._download_file(
                        item['cover_url'],
                        save_dir / f"{work_id}_cover.jpg"
                    )
                    if local_path:
                        s3_url = self.data_manager.upload_to_s3(
                            str(local_path), '', os.path.basename(str(local_path)))
                        if s3_url:
                            cover_s3_url = s3_url
                            self.logger.info(f"    ✅ 封面上传成功")
                except Exception as e:
                    self.logger.warning(f"    ⚠️  封面处理失败: {e}")
            
            # 写入 TXT 文件
            if video_s3_url:
                self.data_manager.append_to_txt(
                    work_url=video_s3_url,
                    site_name=self.category_name,
                    source_url=source_s3_url or '',
                    prompt=item.get('prompt', ''),
                    cover_url=cover_s3_url or ''
                )
                self.logger.info(f"    ✅ 已写入TXT文件")
            
        except Exception as e:
            self.logger.error(f"    ❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _download_file(self, url, save_path):
        """下载文件"""
        try:
            response = requests.get(url, timeout=60, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return save_path
        except Exception as e:
            self.logger.error(f"      下载失败: {e}")
            return None
    
    def errback_httpbin(self, failure):
        """错误回调"""
        self.logger.error(f"❌ 请求失败: {failure.request.url}")
        self.logger.error(f"   原因: {failure.value}")


def run_spider(data_manager, target_count=20, categories=None):
    """运行 Scrapy Spider"""
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    
    # 配置
    settings = get_project_settings()
    settings.update({
        'LOG_LEVEL': 'INFO',
    })
    
    # 创建爬虫进程
    process = CrawlerProcess(settings)
    
    # 运行爬虫
    crawler = process.create_crawler(PixverseSpider)
    process.crawl(
        crawler,
        target_count=target_count,
        data_manager=data_manager,
        categories=categories
    )
    
    process.start()
    
    # 返回爬取数量
    spider = crawler.spider
    return spider.scraped_count if spider else 0

