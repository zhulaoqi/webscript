"""
自定义爬虫示例
演示如何创建自己的爬虫
"""
import sys
sys.path.append('..')

from scrapers.base_scraper import BaseScraper
import uuid


class CustomScraper(BaseScraper):
    """自定义爬虫示例"""
    
    def __init__(self, data_manager, target_url, target_count=10):
        super().__init__(data_manager, use_selenium=True)
        self.target_url = target_url
        self.target_count = target_count
    
    def scrape(self) -> int:
        """执行爬取"""
        print(f"开始爬取: {self.target_url}")
        
        try:
            # 访问网站
            self.driver.get(self.target_url)
            import time
            time.sleep(5)
            
            # 这里添加你的爬取逻辑
            # 1. 查找视频元素
            # 2. 提取视频信息
            # 3. 下载视频文件
            # 4. 保存数据
            
            # 示例：假设我们找到了一些视频
            count = 0
            for i in range(min(5, self.target_count)):
                video_data = {
                    'id': str(uuid.uuid4())[:8],
                    'category': 'Custom',
                    'prompt': f'Sample video {i+1}',
                    'video_path': None,
                    'thumbnail_path': None,
                    'video_url': f'https://example.com/video{i+1}.mp4',
                    'thumbnail_url': f'https://example.com/thumb{i+1}.jpg',
                }
                
                self.data_manager.add_text2video(video_data)
                count += 1
            
            return count
            
        except Exception as e:
            print(f"爬取失败: {e}")
            return 0


def main():
    """测试自定义爬虫"""
    from utils import DataManager
    
    data_manager = DataManager('./custom_downloads')
    
    # 创建自定义爬虫
    scraper = CustomScraper(
        data_manager,
        target_url='https://example.com',
        target_count=10
    )
    
    try:
        count = scraper.scrape()
        print(f"爬取完成: {count} 条")
        
        # 保存数据
        data_manager.save_json()
        
    finally:
        scraper.close()


if __name__ == '__main__':
    main()


