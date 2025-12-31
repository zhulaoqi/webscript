"""
基础爬虫类 - 基于 Scrapy 框架
专业爬虫实现，使用行业标准工具
"""
from abc import ABC, abstractmethod
from utils import DataManager
import logging


class BaseScraper(ABC):
    """基础爬虫抽象类"""
    
    def __init__(self, data_manager: DataManager):
        """
        初始化爬虫
        
        Args:
            data_manager: 数据管理器
        """
        self.data_manager = data_manager
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def scrape(self) -> int:
        """
        执行爬取
        
        Returns:
            爬取的数据条数
        """
        pass
    
    def close(self):
        """关闭资源"""
        pass

