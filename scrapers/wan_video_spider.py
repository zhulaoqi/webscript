"""
Wan Video Spider - 基于 Scrapy 框架
专业爬虫实现，给网址就能自动爬取
"""
import scrapy
from scrapy.http import Request
import json
import uuid
import os
from pathlib import Path
from typing import Dict, Optional
import requests


class WanVideoSpider(scrapy.Spider):
    """Wan Video 爬虫 - Scrapy 版本"""
    
    name = 'wan_video'
    allowed_domains = ['wan.video', 'wanxai.com']
    start_urls = ['https://create.wan.video/']
    
    custom_settings = {
        # 下载延迟（礼貌爬取）
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        
        # 并发设置
        'CONCURRENT_REQUESTS': 4,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        
        # 重试设置
        'RETRY_TIMES': 3,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        
        # User-Agent
        'USER_AGENT': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        
        # 日志级别
        'LOG_LEVEL': 'INFO',
        
        # 自动限速
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 10,
        
        # 中间件
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
            'scrapy_user_agents.middlewares.RandomUserAgentMiddleware': 400,
        }
    }
    
    def __init__(self, target_count=50, data_manager=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_count = int(target_count)
        self.data_manager = data_manager
        self.scraped_count = 0
        self.category_name = 'WanVideo'  # 去掉空格
        
        # 确保有 data_manager
        if not self.data_manager:
            self.logger.error("❌ data_manager 未提供！")
            raise ValueError("data_manager is required")
    
    def parse(self, response):
        """解析首页，直接调用真实 API"""
        self.logger.info(f"🎯 使用真实 API 获取作品列表")
        
        # 真实的 API 地址（从 Network 分析得到）
        api_url = 'https://create.wan.video/wanx/api/v2/square/recommend'
        
        # 请求参数
        payload = {
            'pageSize': self.target_count,
            'source': 'task_image',
            'mediaType': 'all',
            'token': ''  # 第一页为空，后续分页会用到
        }
        
        # 发送 POST 请求
        yield Request(
            url=api_url,
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'x-platform': 'web',
            },
            body=json.dumps(payload),
            callback=self.parse_api,
            errback=self.errback_httpbin
        )
    
    def parse_api(self, response):
        """解析真实 API 响应"""
        try:
            data = json.loads(response.text)
            
            if not data.get('success'):
                self.logger.error(f"❌ API 返回失败: {data.get('errorMsg', '未知错误')}")
                return
            
            # 提取作品列表
            works = data.get('data', {}).get('works', [])
            
            if not works:
                self.logger.warning(f"⚠️  未找到作品数据")
                return
            
            self.logger.info(f"✅ 获取到 {len(works)} 个作品")
            
            # 遍历每个作品
            for work_item in works:
                if work_item.get('type') != 'WORK':
                    continue
                
                work_data = work_item.get('data', {})
                
                # 提取关键信息
                media_type = work_data.get('mediaType')  # "video" 或 "image"
                task_type = work_data.get('taskType')    # "text_to_video", "image_to_video" 等
                task_input = work_data.get('taskInput', {})
                image_info = work_data.get('image', {})
                
                # 构造标准化数据
                item = {
                    'id': work_data.get('resourceId'),
                    'type': 'image2video' if 'image_to' in task_type else 'text2video',
                    'media_type': media_type,
                    'prompt': task_input.get('prompt') or task_input.get('finalPrompt', 'No prompt'),
                    
                    # 视频/图片 URL
                    'video_url': image_info.get('downloadUrl') if media_type == 'video' else image_info.get('url'),
                    'cover_url': image_info.get('resizeUrl') or image_info.get('url'),
                    
                    # 原图 URL（图生视频才有）
                    'source_image_url': None,
                }
                
                # 提取原图（如果有）
                ref_images = task_input.get('refImagesurlsInfo', [])
                if ref_images and len(ref_images) > 0:
                    item['source_image_url'] = ref_images[0].get('originImage')
                    item['type'] = 'image2video'
                
                # 计数控制
                if self.scraped_count >= self.target_count:
                    self.logger.info(f"✅ 已达到目标数量: {self.target_count}")
                    return
                
                self.scraped_count += 1
                self.logger.info(f"  [{self.scraped_count}/{self.target_count}] {item['type']} - {item['prompt'][:50]}...")
                
                # 下载并上传到 S3
                self._process_work(item)
                
                yield item
            
            # 分页：获取下一页
            next_token = data.get('data', {}).get('token')
            if next_token and self.scraped_count < self.target_count:
                self.logger.info(f"📄 继续获取下一页...")
                
                payload = {
                    'pageSize': self.target_count - self.scraped_count,
                    'source': 'task_image',
                    'mediaType': 'all',
                    'token': next_token
                }
                
                yield Request(
                    url='https://create.wan.video/wanx/api/v2/square/recommend',
                    method='POST',
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                        'x-platform': 'web',
                    },
                    body=json.dumps(payload),
                    callback=self.parse_api,
                    dont_filter=True
                )
                
        except json.JSONDecodeError:
            self.logger.warning(f"⚠️  API 响应不是 JSON")
        except Exception as e:
            self.logger.error(f"❌ 解析 API 失败: {e}")
            import traceback
            traceback.print_exc()
    
    def parse_work(self, response):
        """解析作品详情页"""
        self.logger.info(f"📄 解析作品: {response.url}")
        
        # 提取视频URL
        video_urls = response.css('video source::attr(src), video::attr(src)').getall()
        
        # 提取图片URL
        image_urls = response.css('img[src*="wanxai.com"]::attr(src)').getall()
        
        # 提取提示词
        prompt = response.css('.prompt::text, [class*="prompt"]::text').get() or 'No prompt'
        
        if video_urls or image_urls:
            yield {
                'url': response.url,
                'video_url': video_urls[0] if video_urls else None,
                'cover_url': image_urls[0] if image_urls else None,
                'prompt': prompt.strip(),
                'type': 'text2video',
            }
    
    def _extract_json_from_script(self, script_text: str) -> Optional[Dict]:
        """从 <script> 标签中提取 JSON"""
        try:
            # 尝试提取 window.__INITIAL_STATE__ 或类似变量
            import re
            
            patterns = [
                r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                r'window\.__NEXT_DATA__\s*=\s*({.+?})</script>',
                r'var\s+\w+\s*=\s*({.+?});',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, script_text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    return json.loads(json_str)
            
            return None
        except:
            return None
    
    def _parse_json_data(self, data: Dict) -> list:
        """从 JSON 中提取作品列表"""
        # 递归查找数组数据
        def find_arrays(obj, depth=0):
            if depth > 5:  # 限制递归深度
                return []
            
            if isinstance(obj, list) and len(obj) > 0:
                # 检查是否是作品数组（包含 url/video 等字段）
                if isinstance(obj[0], dict):
                    keys = obj[0].keys()
                    if any(k in keys for k in ['url', 'video', 'id', 'src']):
                        return obj
            
            if isinstance(obj, dict):
                for value in obj.values():
                    result = find_arrays(value, depth + 1)
                    if result:
                        return result
            
            return []
        
        return find_arrays(data)
    
    def _create_work_item(self, work: Dict) -> Dict:
        """创建标准化的作品数据"""
        # 智能提取字段（适配不同的 API 响应格式）
        def get_value(data, keys):
            for key in keys:
                if key in data and data[key]:
                    return data[key]
            return None
        
        return {
            'id': get_value(work, ['id', 'video_id', '_id']),
            'video_url': get_value(work, ['video_url', 'videoUrl', 'url', 'video', 'media_url']),
            'cover_url': get_value(work, ['cover_url', 'coverUrl', 'cover', 'thumbnail', 'poster']),
            'prompt': get_value(work, ['prompt', 'description', 'text', 'caption']) or 'No prompt',
            'source_image_url': get_value(work, ['source_image_url', 'sourceImageUrl', 'source', 'input_image']),
            'type': 'image2video' if get_value(work, ['source_image_url', 'source']) else 'text2video',
        }
    
    def _process_work(self, item):
        """处理作品：下载、上传、写入TXT"""
        try:
            
            work_id = item['id'][:8] if item.get('id') else str(self.scraped_count)
            work_type = item['type']
            
            # 确定保存目录
            if work_type == 'image2video':
                save_dir = self.data_manager.image2video_dir / 'wan_video'
            else:
                save_dir = self.data_manager.text2video_dir / 'wan_video'
            
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
    crawler = process.create_crawler(WanVideoSpider)
    process.crawl(
        crawler,
        target_count=target_count,
        data_manager=data_manager
    )
    
    process.start()
    
    # 返回爬取数量
    spider = crawler.spider
    return spider.scraped_count if spider else 0

