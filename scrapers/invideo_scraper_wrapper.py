"""
InVideo Scraper Wrapper - Playwright 爬虫封装
"""
from .invideo_spider import InVideoSpider
from .base_scraper import BaseScraper


class InvideoScraper(BaseScraper):
    def __init__(self, data_manager, target_count: int = 50, categories: list = None):
        super().__init__(data_manager)
        self.target_count = target_count
        # 默认类别
        self.categories = categories or [
            'Million Dollar Ads',
            'UGC & Avatars'
        ]
        self.spider = None
    
    def scrape(self) -> int:
        try:
            self.spider = InVideoSpider(
                target_count=self.target_count,
                data_manager=self.data_manager,
                categories=self.categories
            )
            count = self.spider.scrape()
            return count
        except Exception as e:
            print(f"❌ 爬取失败: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def close(self):
        if self.spider:
            self.spider.close()

