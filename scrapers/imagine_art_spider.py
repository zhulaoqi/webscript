"""
Imagine.art Spider - 基于 Scrapy 框架
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


class ImagineArtSpider(scrapy.Spider):
    name = 'imagine_art'
    
    # API 配置
    api_url = 'https://imagine-blog.vyro.ai/api/video-feeds'
    base_url = 'https://imagine.animagic.art/imagine-dashboard'  # ✅ 正确的素材域名
    
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'zh-CN,zh;q=0.9',
        'authorization': 'Bearer 8aef257cdbd1f6a03c0c2c3030a8a5fe3c1e3d128c95cdafa2ac71ceaf8f49af3ec23cc1fd0d443882b4297b97d901cb8d5d9f3d124afe15e51fb40c2e1b3a3b66d56bd1d17d3cb52a1a89b71fff53ca8d9c695c5e8736be498c379183d5429f519d7d79ee6265c03e060eee1d51dd58feb826bc869dd4e01299f915629cb005',
        'origin': 'https://www.imagine.art',
        'referer': 'https://www.imagine.art/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
    }
    
    def __init__(self, target_count=50, data_manager=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_count = int(target_count)
        self.data_manager = data_manager
        self.scraped_count = 0
        self.category_name = 'ImagineArt'
        self.current_page = 1
        
        # 确保有 data_manager
        if not self.data_manager:
            self.logger.error("❌ data_manager 未提供！")
            raise ValueError("data_manager is required")
    
    def start_requests(self):
        """开始请求第一页"""
        yield self._make_request(page=1)
    
    def _make_request(self, page):
        """构造 API 请求"""
        params = {
            'populate[category][fields][0]': '*',
            'pagination[page]': page,
            'pagination[pageSize]': 50,
        }
        
        url = self.api_url + '?' + '&'.join([f"{k}={v}" for k, v in params.items()])
        
        return scrapy.Request(
            url=url,
            headers=self.headers,
            callback=self.parse_api,
            errback=self.errback_httpbin,
            dont_filter=True,
            meta={'page': page}
        )
    
    def parse_api(self, response):
        """解析 API 响应"""
        try:
            data = json.loads(response.text)
            page = response.meta['page']
            
            self.logger.info(f"✅ API 响应成功: 第 {page} 页")
            
            items = data.get('data', [])
            pagination = data.get('meta', {}).get('pagination', {})
            
            self.logger.info(f"   找到 {len(items)} 个作品")
            self.logger.info(f"   分页信息: {page}/{pagination.get('pageCount', '?')}")
            
            # 处理每个作品
            for item_data in items:
                if self.scraped_count >= self.target_count:
                    raise CloseSpider('Target count reached')
                
                item = self._extract_work_data(item_data)
                if item:
                    self.scraped_count += 1
                    self._process_work(item)
                    self.logger.info(f"   ✅ 提取作品 [{self.scraped_count}/{self.target_count}]")
            
            # 自动翻页
            if self.scraped_count < self.target_count:
                next_page = page + 1
                page_count = pagination.get('pageCount', 0)
                
                if next_page <= page_count:
                    self.logger.info(f"   ⏩ 翻页到第 {next_page} 页...")
                    yield self._make_request(page=next_page)
                else:
                    self.logger.info(f"   ℹ️  已到最后一页")
        
        except CloseSpider as e:
            self.logger.info(f"🏁 爬取完成: {e}")
            raise
        except json.JSONDecodeError:
            self.logger.warning(f"⚠️  API 响应不是 JSON: {response.url}")
        except Exception as e:
            self.logger.error(f"❌ 解析 API 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_work_data(self, item_data):
        """提取作品数据"""
        try:
            attrs = item_data.get('attributes', {})
            
            # 获取分类
            category = attrs.get('category', {}).get('data', {}).get('attributes', {}).get('label', '')
            
            # 判断类型
            work_type = 'text2video'
            if category == 'Image to Video' or attrs.get('settings', {}).get('generated_from_image'):
                work_type = 'image2video'
            
            # 提取 URL
            video_path = attrs.get('videoHd') or attrs.get('video', '')
            image_path = attrs.get('settings', {}).get('generated_from_image') or attrs.get('image', '')
            
            video_url = self.base_url + video_path if video_path else ''
            source_image_url = self.base_url + image_path if image_path and work_type == 'image2video' else ''
            cover_url = self.base_url + attrs.get('image', '') if attrs.get('image') else ''
            
            return {
                'id': str(item_data.get('id', '')),
                'prompt': attrs.get('prompt', ''),
                'video_url': video_url,
                'source_image_url': source_image_url,
                'cover_url': cover_url,
                'type': work_type,
                'media_type': 'video' if video_path.endswith('.mp4') else 'image',
            }
        
        except Exception as e:
            self.logger.error(f"提取作品数据失败: {e}")
            return None
    
    def _process_work(self, item):
        """处理作品：下载、上传、写入TXT"""
        try:
            work_id = item['id'][:8] if item.get('id') else str(self.scraped_count)
            work_type = item['type']
            
            # 确定保存目录
            if work_type == 'image2video':
                save_dir = self.data_manager.image2video_dir / self.category_name
            else:
                save_dir = self.data_manager.text2video_dir / self.category_name
            
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
            
            # 下载视频/图片
            if item.get('video_url'):
                try:
                    ext = '.mp4' if item.get('media_type') == 'video' else '.jpg'
                    self.logger.info(f"    📥 下载{'视频' if ext == '.mp4' else '图片'}...")
                    
                    local_path = self._download_file(
                        item['video_url'],
                        save_dir / f"{work_id}_video{ext}"
                    )
                    if local_path:
                        s3_url = self.data_manager.upload_to_s3(
                            str(local_path), '', os.path.basename(str(local_path)))
                        if s3_url:
                            video_s3_url = s3_url
                            self.logger.info(f"    ✅ {'视频' if ext == '.mp4' else '图片'}上传成功")
                except Exception as e:
                    self.logger.warning(f"    ⚠️  视频/图片处理失败: {e}")
            
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


def run_spider(data_manager, target_count=50):
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
    crawler = process.create_crawler(ImagineArtSpider)
    process.crawl(
        crawler,
        target_count=target_count,
        data_manager=data_manager
    )
    
    process.start()
    
    # 返回爬取数量
    spider = crawler.spider
    return spider.scraped_count if spider else 0

