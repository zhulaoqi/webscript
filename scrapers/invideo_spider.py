"""
InVideo Spider - 基于 DOC 请求精准解析
逻辑：先请求 DOC 获取完整 HTML，从中精准解析视频对象和提示词，然后下载
"""
from playwright.sync_api import sync_playwright
import requests
import os
from pathlib import Path
import re
import time
import json


class InVideoSpider:
    name = 'invideo'

    def __init__(self, target_count=50, data_manager=None, categories=None):
        self.target_count = int(target_count)
        self.data_manager = data_manager
        self.category_name = 'InVideo'
        self.scraped_count = 0

        # 支持的类别
        self.categories = categories or [
            'Million Dollar Ads',
            'UGC & Avatars'
        ]

        # 类别名称到 URL section 的映射
        self.category_url_map = {
            'Million Dollar Ads': 'million-dollar-ads',
            'UGC & Avatars': 'ugc-and-avatars'
        }

        # 确保有 data_manager
        if not self.data_manager:
            raise ValueError("data_manager is required")

        # 存储 slot → prompt 映射（从 HTML 提取）
        self.slot_to_prompt = {}

        # 存储解析结果（从 Flight 提取）
        self.results = []

    def _parse_doc_html(self, html_content):
        """
        从 DOC HTML 中解析 __next_f.push 数据
        直接抓取完整的 push([...]) JSON 数组
        """
        
        # 【新方案】直接匹配完整的 push([...]) JSON 数组（去掉结尾 \n 的要求）
        push_blocks = re.findall(r'self\.__next_f\.push\((\[.*?\])\)', html_content, flags=re.DOTALL)
        print(f"📊 正则匹配到 {len(push_blocks)} 个 push 数据块")
        
        # ✅ 两步走策略：
        # 第一步：扫描所有 push，建立 slot → prompt 映射
        # 第二步：扫描所有 push，提取 videos 并解析 prompt 引用
        
        slot_to_prompt = {}
        all_videos_raw = []  # 先收集所有videos（prompt可能是引用）
        
        # ========== 第一步：扫描所有 push，建立 slot → prompt 映射 ==========
        print(f"\n{'='*40} 第一步：提取 slot 映射 {'='*40}")
        current_slot = None  # 用于"延迟绑定"
        
        for push_idx, push in enumerate(push_blocks):
            try:
                outer_data = json.loads(push)
                if not isinstance(outer_data, list) or len(outer_data) < 2:
                    continue
                
                payload = outer_data[1]
                if not isinstance(payload, str):
                    continue
                
                # 检查是否是 slot 声明（如 "25:T457,"）
                slot_match = re.match(r'^(\w+):T[a-f0-9]+,?$', payload)
                if slot_match:
                    current_slot = slot_match.group(1)
                    continue
                
                # 如果前一个是slot声明，且当前是长文本，则绑定
                if current_slot and len(payload) > 80 and 'http' not in payload and not payload.startswith('['):
                    clean_text = payload.replace('\\n', '\n').replace('\\/', '/').replace('\\"', '"')
                    slot_to_prompt[f"${current_slot}"] = clean_text
                    current_slot = None  # 重置
            except:
                continue
        
        print(f"✅ 提取到 {len(slot_to_prompt)} 个提示词映射")
        
        # ========== 第二步：提取 videos ==========
        
        for push_idx, push in enumerate(push_blocks):
            try:
                outer_data = json.loads(push)
                if not isinstance(outer_data, list) or len(outer_data) < 2:
                    continue
                
                payload = outer_data[1]
                if not isinstance(payload, str):
                    continue
                
                # 只关注包含 videos 的 payload
                # 格式：" 1c:[\"$\",\"$L1a\",\"million-dollar-ads\",{\"videos\":[...]}]"
                if ':' in payload and ('[' in payload or 'videos' in payload):
                    # 去掉 slot ID
                    json_part = payload.split(':', 1)[1] if ':' in payload else payload
                    
                    # ✅ 只替换最外层的引号转义，保持JSON有效性
                    # \n、\/ 等由 json.loads 自动处理，不要手动替换！
                    cleaned = json_part.replace('\\"', '"')
                    
                    try:
                        # 解析内层 JSON
                        inner_data = json.loads(cleaned)
                        
                        # 检查结构：["$","$L1a","million-dollar-ads",{...}]
                        if isinstance(inner_data, list) and len(inner_data) >= 4:
                            data_obj = inner_data[-1]
                            
                            # ✅ 只提取我们需要的分类
                            category = inner_data[2] if len(inner_data) >= 3 else ''
                            
                            if isinstance(data_obj, dict) and 'videos' in data_obj:
                                videos = data_obj['videos']
                                
                                # 只处理目标分类
                                if category in ['million-dollar-ads', 'ugc-and-avatars']:
                                    for v in videos:
                                        all_videos_raw.append({
                                            'preview_url': v.get('preview_url', ''),
                                            'prompt': v.get('prompt', ''),
                                            'category': category  # 记录分类
                                        })
                    except (json.JSONDecodeError, Exception):
                        continue
            except:
                continue
        
        print(f"✅ 提取到 {len(all_videos_raw)} 个原始视频")
        
        # ========== 第三步：解析 prompt 引用 ==========
        
        self.results = []
        for idx, video in enumerate(all_videos_raw):
            preview_url = video.get('preview_url', '')
            prompt = video.get('prompt', '')
            category = video.get('category', '')
            
            # 提取 UUID
            uuid_match = re.search(r'/([a-f0-9-]{36})/', preview_url)
            if not uuid_match:
                continue
            
            uuid = uuid_match.group(1)
            
            # 解析 prompt 引用
            final_prompt = ''
            if isinstance(prompt, str):
                if prompt.startswith('$'):
                    # 是引用，查找映射
                    final_prompt = slot_to_prompt.get(prompt, '')
                elif len(prompt) > 10:
                    # 直接是文本
                    final_prompt = prompt
            
            # ✅ 只保存有 prompt 的视频
            if final_prompt:
                self.results.append({
                    'uuid': uuid,
                    'preview_url': preview_url,
                    'prompt': final_prompt,
                    'category': category
                })
        
        # 按分类统计
        category_stats = {}
        for r in self.results:
            cat = r.get('category', 'unknown')
            category_stats[cat] = category_stats.get(cat, 0) + 1
        
        print(f"✅ 最终: {len(self.results)} 个视频 (过滤: {len(all_videos_raw) - len(self.results)})")
        for cat, count in category_stats.items():
            print(f"   - {cat}: {count} 个")

    def scrape(self):
        """执行爬取"""
        print(f"\n🚀 启动 InVideo Playwright 爬虫...")
        print(f"   目标: {self.target_count} 条")
        print(f"   分类: {', '.join(self.categories)}")
        print(f"   方法: DOC 请求 + 精准解析")
        print("=" * 60)

        try:
            # 确定保存目录
            save_dir = self.data_manager.text2video_dir / self.category_name
            save_dir.mkdir(exist_ok=True, parents=True)

            all_results = []  # 存储所有分类的结果

            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(
                    headless=False,
                    slow_mo=50,
                    args=['--disable-blink-features=AutomationControlled']
                )

                context = browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    viewport={'width': 1280, 'height': 800},
                    locale='en-US',
                    timezone_id='America/Los_Angeles'
                )

                page = context.new_page()
                page.set_default_timeout(60000)

                # 遍历每个分类
                for category in self.categories:
                    if self.scraped_count >= self.target_count:
                        print(f"   ℹ️  已达到目标数量 {self.target_count}，停止爬取")
                        break

                    section_url = self.category_url_map.get(category, '')
                    if not section_url:
                        print(f"   ⚠️  未找到分类 '{category}' 的 URL 映射，跳过")
                        continue

                    doc_url = f'https://invideo.io/ideas/?section={section_url}'
                    print(f"\n🌐 爬取分类: {category}")
                    print(f"   URL: {doc_url}")

                    # 清空结果
                    self.results = []

                    # 【核心】只需要请求 DOC HTML，videos 已经在 RSC 流里
                    print(f"   📄 请求 DOC HTML（包含 RSC 数据流）...")
                    try:
                        response = page.request.get(doc_url)
                        if response.status != 200:
                            print(f"   ❌ 请求失败: HTTP {response.status}")
                            continue

                        html_content = response.text()
                        print(f"   ✅ 请求成功 ({len(html_content)} 字节)")

                        # 解析 RSC 数据流：slot + videos
                        print(f"   📝 解析 RSC 数据流...")
                        self._parse_doc_html(html_content)
                    except Exception as e:
                        print(f"   ❌ 请求失败: {e}")
                        continue

                    # 检查是否解析到数据
                    if not self.results:
                        print(f"   ⚠️  未解析到视频数据，跳过此分类")
                        continue

                    # 下载视频
                    print(f"   📥 开始下载视频...")
                    for video in self.results:
                        if self.scraped_count >= self.target_count:
                            break

                        uuid = video['uuid']
                        preview_url = video['preview_url']
                        prompt = video.get('prompt', '')

                        work_id = uuid[:16]

                        print(f"\n   📹 [{self.scraped_count + 1}] 下载: {work_id}")
                        print(f"      【步骤3-从results读取】提示词长度: {len(prompt)} 字符")
                        print(f"      【步骤3-从results读取】完整内容:")
                        print(f"      {prompt}")

                        # 下载视频
                        try:
                            response = page.request.get(preview_url)
                            if response.status == 200:
                                content = response.body()

                                save_path = save_dir / f"{work_id}_video.webm"
                                with open(save_path, 'wb') as f:
                                    f.write(content)

                                file_size = len(content) / 1024 / 1024
                                print(f"      ✅ 下载成功: {save_path.name} ({file_size:.2f} MB)")

                                # 记录结果
                                print(f"      【步骤4-保存到all_results前】提示词长度: {len(prompt)} 字符")
                                all_results.append({
                                    'id': work_id,
                                    'local_path': save_path,
                                    'video_url': preview_url,
                                    'prompt': prompt,
                                    'type': 'text2video',
                                    'cover_url': '',
                                    'source_image_url': ''
                                })
                                print(f"      【步骤4-保存到all_results后】验证: {len(all_results[-1]['prompt'])} 字符")

                                self.scraped_count += 1
                            else:
                                print(f"      ❌ 下载失败: HTTP {response.status}")

                        except Exception as e:
                            print(f"      ❌ 下载失败: {e}")

                    print(f"   ✅ 分类 '{category}' 完成，共 {self.scraped_count} 个视频")

                browser.close()

            # 第4步：上传到 S3 并保存到 Excel
            print(f"\n☁️  开始上传到 S3...")
            for idx, result in enumerate(all_results, 1):
                print(f"\n[{idx}/{len(all_results)}] 处理视频 {result['id']}")
                print(f"   【步骤5-从all_results读取】提示词长度: {len(result['prompt'])} 字符")

                # 上传到 S3
                filename = Path(result['local_path']).name
                s3_url = self.data_manager.upload_to_s3(
                    result['local_path'],
                    category=self.category_name,  # InVideo
                    filename=filename
                )

                if s3_url:
                    # 保存到 Excel（格式：["作品URL", "原图URL", "提示词", "缩略图URL"]）
                    prompt_to_save = result['prompt']
                    print(f"   【步骤6-写入Excel前】提示词长度: {len(prompt_to_save)} 字符")
                    print(f"   【步骤6-写入Excel前】完整内容:")
                    print(f"   {prompt_to_save}")
                    print(f"   {'='*80}")
                    
                    self.data_manager.excel_data.setdefault(self.category_name, []).append([
                        s3_url,           # 作品URL
                        '',               # 原图URL（视频没有）
                        prompt_to_save,   # 提示词（完整）
                        ''                # 缩略图URL（暂无）
                    ])
                    
                    # 立即验证写入的数据
                    saved_row = self.data_manager.excel_data[self.category_name][-1]
                    print(f"   【步骤6-写入Excel后】验证提示词长度: {len(saved_row[2])} 字符")
                    print(f"   ✅ 已写入数据到内存")

            print(f"\n🏁 爬取完成！共 {len(all_results)} 条")
            return len(all_results)

        except Exception as e:
            print(f"❌ 爬取失败: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def close(self):
        """关闭爬虫（清理资源）"""
        pass
