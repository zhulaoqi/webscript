"""
爬虫模块 - 基于 Scrapy 框架（专业爬虫）
"""
# Scrapy 爬虫实现
from .wan_scraper_wrapper import WanVideoScraper
from .imagine_art_scraper_wrapper import ImagineArtScraper
from .pixverse_scraper_wrapper import PixverseScraper

# Playwright 网络监听（特殊情况：无 API 网站）
from .invideo_scraper_wrapper import InvideoScraper

# 其他网站暂未实现
HiggsfieldScraper = None

__all__ = [
    'WanVideoScraper',
    'HiggsfieldScraper',
    'ImagineArtScraper',
    'InvideoScraper',
    'PixverseScraper'
]

