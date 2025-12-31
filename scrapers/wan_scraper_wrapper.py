"""
Wan Video 爬虫包装器
将 Scrapy Spider 包装成统一接口
"""
from .base_scraper import BaseScraper
from .wan_video_spider import run_spider


class WanVideoScraper(BaseScraper):
    """Wan Video 爬虫 - Scrapy 实现"""
    
    def __init__(self, data_manager, target_count: int = 50):
        super().__init__(data_manager)
        self.target_count = target_count
    
    def scrape(self) -> int:
        """执行爬取"""
        print(f"\n🚀 启动 Scrapy 爬虫...")
        print(f"   目标: {self.target_count} 条")
        print(f"   框架: Scrapy (专业爬虫框架)")
        print("=" * 60)
        
        try:
            count = run_spider(self.data_manager, self.target_count)
            return count
        except Exception as e:
            print(f"❌ 爬取失败: {e}")
            import traceback
            traceback.print_exc()
            return 0

