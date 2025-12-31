"""
批量下载示例
演示如何批量下载多个网站的素材
"""
import sys
sys.path.append('..')

from utils import DataManager
from scrapers import (
    WanVideoScraper,
    HiggsfieldScraper,
    ImagineArtScraper
)


def main():
    """批量下载示例"""
    
    data_manager = DataManager('./batch_downloads')
    
    scrapers = [
        ('Wan Video', WanVideoScraper(data_manager, target_count=10)),
        ('Higgsfield', HiggsfieldScraper(data_manager, target_count_per_category=5)),
        ('Imagine.art', ImagineArtScraper(data_manager, target_count=10)),
    ]
    
    total_count = 0
    
    for name, scraper in scrapers:
        print(f"\n{'='*60}")
        print(f"开始爬取: {name}")
        print('='*60)
        
        try:
            count = scraper.scrape()
            total_count += count
            print(f"✓ {name} 完成: {count} 条")
        except Exception as e:
            print(f"✗ {name} 失败: {e}")
        finally:
            scraper.close()
    
    # 保存所有数据
    print(f"\n{'='*60}")
    print("保存数据...")
    data_manager.save_json()
    data_manager.export_excel()
    
    # 创建压缩包
    zip_path = data_manager.create_zip()
    
    # 显示摘要
    summary = data_manager.get_summary()
    print(f"\n{'='*60}")
    print("批量下载完成！")
    print('='*60)
    print(f"总计: {summary['total_count']} 条")
    print(f"- 文生视频: {summary['text2video_count']}")
    print(f"- 图生视频: {summary['image2video_count']}")
    print('='*60)


if __name__ == '__main__':
    main()


