#!/usr/bin/env python3
"""
AI视频素材爬虫主程序

从多个AI视频生成网站爬取素材：
- Wan Video
- Higgsfield.ai
- Imagine.art
- InVideo.io
- Pixverse.ai
"""
import sys
import argparse
from pathlib import Path
from config import OUTPUT_DIR, WEBSITES
from utils import DataManager
from scrapers import (
    WanVideoScraper,
    HiggsfieldScraper,
    ImagineArtScraper,
    InvideoScraper,
    PixverseScraper
)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='AI视频素材爬虫')
    parser.add_argument(
        '--sites',
        nargs='+',
        choices=['wan', 'higgsfield', 'imagine', 'invideo', 'pixverse', 'all'],
        default=['all'],
        help='要爬取的网站 (默认: all)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=OUTPUT_DIR,
        help=f'输出目录 (默认: {OUTPUT_DIR})'
    )
    parser.add_argument(
        '--no-zip',
        action='store_true',
        help='不创建ZIP压缩包'
    )
    
    args = parser.parse_args()
    
    # 初始化数据管理器
    data_manager = DataManager(args.output)
    
    print("=" * 60)
    print("AI视频素材爬虫")
    print("=" * 60)
    print(f"输出目录: {args.output}")
    print(f"目标网站: {', '.join(args.sites)}")
    print("=" * 60)
    
    # 确定要爬取的网站
    sites_to_scrape = args.sites
    if 'all' in sites_to_scrape:
        sites_to_scrape = ['wan', 'higgsfield', 'imagine', 'invideo', 'pixverse']
    
    total_scraped = 0
    
    try:
        # 爬取 Wan Video (新的超简单版本)
        if 'wan' in sites_to_scrape:
            try:
                scraper = WanVideoScraper(
                    data_manager,
                    target_count=WEBSITES['wan_video']['target_count']
                )
                count = scraper.scrape()
                total_scraped += count
                scraper.close()
                print(f"✓ Wan Video 完成: {count} 条 (已实时写入TXT)")
            except Exception as e:
                print(f"✗ Wan Video 失败: {e}")
                import traceback
                traceback.print_exc()
        
        # 爬取 Higgsfield
        if 'higgsfield' in sites_to_scrape:
            if HiggsfieldScraper is None:
                print("⚠️  Higgsfield 爬虫暂未实现（需要改造为 API 版本）")
            else:
                try:
                    scraper = HiggsfieldScraper(
                        data_manager,
                        target_count_per_category=WEBSITES['higgsfield']['target_count']
                    )
                    count = scraper.scrape()
                    total_scraped += count
                    scraper.close()
                    print(f"✓ Higgsfield 完成: {count} 条 (已实时写入TXT)")
                except Exception as e:
                    print(f"✗ Higgsfield 失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 爬取 Imagine.art
        if 'imagine' in sites_to_scrape:
            if ImagineArtScraper is None:
                print("⚠️  Imagine.art 爬虫暂未实现（需要改造为 API 版本）")
            else:
                try:
                    scraper = ImagineArtScraper(
                        data_manager,
                        target_count=WEBSITES['imagine_art']['target_count']
                    )
                    count = scraper.scrape()
                    total_scraped += count
                    scraper.close()
                    print(f"✓ Imagine.art 完成: {count} 条 (已实时写入TXT)")
                except Exception as e:
                    print(f"✗ Imagine.art 失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 爬取 InVideo
        if 'invideo' in sites_to_scrape:
            if InvideoScraper is None:
                print("⚠️  InVideo 爬虫暂未实现（需要改造为 API 版本）")
            else:
                try:
                    scraper = InvideoScraper(
                        data_manager,
                        target_count_per_category=WEBSITES['invideo']['target_count']
                    )
                    count = scraper.scrape()
                    total_scraped += count
                    scraper.close()
                    print(f"✓ InVideo 完成: {count} 条 (已实时写入TXT)")
                except Exception as e:
                    print(f"✗ InVideo 失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        # 爬取 Pixverse
        if 'pixverse' in sites_to_scrape:
            if PixverseScraper is None:
                print("⚠️  Pixverse 爬虫暂未实现（需要改造为 API 版本）")
            else:
                try:
                    scraper = PixverseScraper(
                        data_manager,
                        target_count=WEBSITES['pixverse']['target_count'],
                        categories=WEBSITES['pixverse'].get('categories')
                    )
                    count = scraper.scrape()
                    total_scraped += count
                    scraper.close()
                    print(f"✓ Pixverse 完成: {count} 条 (已实时写入TXT)")
                except Exception as e:
                    print(f"✗ Pixverse 失败: {e}")
                    import traceback
                    traceback.print_exc()
        
        # TXT已实时写入
        print("\n" + "=" * 60)
        print("✅ 所有URL已实时写入TXT文件")
        
        # 显示摘要
        summary = data_manager.get_summary()
        print("\n" + "=" * 60)
        print("✓ 爬取完成！")
        print("=" * 60)
        print(f"文生视频: {summary['text2video_count']} 条")
        print(f"图生视频: {summary['image2video_count']} 条")
        print(f"总计: {summary['total_count']} 条")
        print(f"\n📄 TXT文件位置: {OUTPUT_DIR}/")
        print("=" * 60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
        return 1
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

