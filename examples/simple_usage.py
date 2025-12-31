"""
简单使用示例
"""
import sys
sys.path.append('..')

from utils import DataManager
from scrapers import WanVideoScraper


def main():
    """简单示例：只爬取 Wan Video"""
    
    # 创建数据管理器
    data_manager = DataManager('./test_downloads')
    
    # 创建爬虫
    scraper = WanVideoScraper(data_manager, target_count=5)
    
    try:
        # 执行爬取
        count = scraper.scrape()
        print(f"\n成功爬取 {count} 条数据")
        
        # 保存数据
        data_manager.save_json()
        
        # 显示摘要
        summary = data_manager.get_summary()
        print(f"\n数据摘要：")
        print(f"- 文生视频: {summary['text2video_count']}")
        print(f"- 图生视频: {summary['image2video_count']}")
        
    finally:
        scraper.close()


if __name__ == '__main__':
    main()


