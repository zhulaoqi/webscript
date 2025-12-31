"""
Imagine.art 网站爬虫 - 简化版
"""
from .simple_scraper_template import SimpleMediaScraper


class ImagineArtScraper(SimpleMediaScraper):
    """Imagine Art 爬虫 - 简化版"""
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager, use_selenium=True)
        self.target_count = target_count
        self.base_url = 'https://www.imagine.art/community'  # 改为community页面
    
    def scrape(self) -> int:
        """执行爬取 - 使用简化模板"""
        return self.scrape_simple(
            url=self.base_url,
            category='Imagine.art',
            target_count=self.target_count
        )

