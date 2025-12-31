"""
Pixverse Scraper Wrapper - Scrapy 爬虫封装
"""
import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from .pixverse_spider import PixverseSpider
from .base_scraper import BaseScraper


class PixverseScraper(BaseScraper):
    def __init__(self, data_manager, target_count: int = 20, categories: list = None):
        super().__init__(data_manager)
        self.target_count = target_count
        self.process = None
        # 默认类别
        self.categories = categories or [
            'Winter Vibe',
            'Ad Magic',
            'Cinematic Narrative',
            'Stylistic Art',
            'Animal Theatre',
            'Effects Rendering',
            'Emotional Close-up'
        ]
    
    def scrape(self) -> int:
        print(f"\n🚀 启动 Pixverse Scrapy 爬虫...")
        print(f"   目标: {self.target_count} 条/类别")
        print(f"   类别数: {len(self.categories)}")
        print(f"   总计: {self.target_count * len(self.categories)} 条")
        print(f"   框架: Scrapy (专业爬虫框架)")
        print("=" * 60)
        
        settings = get_project_settings()
        settings.set('LOG_LEVEL', 'INFO')
        settings.set('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36')
        settings.set('DOWNLOAD_DELAY', 1)
        settings.set('CONCURRENT_REQUESTS_PER_DOMAIN', 3)
        settings.set('AUTOTHROTTLE_ENABLED', True)
        settings.set('RETRY_TIMES', 3)
        
        self.process = CrawlerProcess(settings)
        crawler = self.process.create_crawler(PixverseSpider)
        self.process.crawl(
            crawler,
            data_manager=self.data_manager,
            target_count=self.target_count,
            categories=self.categories
        )
        self.process.start()
        
        return crawler.spider.scraped_count if crawler.spider else 0
    
    def close(self):
        if self.process:
            self.process.stop()

