#!/usr/bin/env python3
"""
测试新的详细爬虫导入
"""

print("=" * 60)
print("测试导入所有详细爬虫...")
print("=" * 60)

try:
    print("\n1. 导入 WanVideoScraper...")
    from scrapers import WanVideoScraper
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n2. 导入 HiggsfieldScraper...")
    from scrapers import HiggsfieldScraper
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n3. 导入 ImagineArtScraper...")
    from scrapers import ImagineArtScraper
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n4. 导入 InvideoScraper...")
    from scrapers import InvideoScraper
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

try:
    print("\n5. 导入 PixverseScraper...")
    from scrapers import PixverseScraper
    print("   ✅ 成功")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print("\n" + "=" * 60)
print("✅ 所有爬虫导入成功！")
print("=" * 60)
print("\n现在可以运行: ./start.sh")


