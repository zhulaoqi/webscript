"""
Pixverse.ai 网站爬虫 - 简化版
"""
from .simple_scraper_template import SimpleMediaScraper


class PixverseScraper(SimpleMediaScraper):
    """Pixverse 爬虫 - 简化版"""
    
    def __init__(self, data_manager, target_count_per_category: int = 50):
        super().__init__(data_manager, use_selenium=True)
        self.target_count = target_count_per_category  # 现在表示总数
        self.base_url = 'https://app.pixverse.ai/onboard'
    
    def scrape(self) -> int:
        """执行爬取 - 使用简化模板"""
        return self.scrape_simple(
            url=self.base_url,
            category='Pixverse',
            target_count=self.target_count  # 直接使用总数，不再乘以分类数
        )

