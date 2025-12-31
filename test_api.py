"""
API 测试工具
用于快速测试从浏览器复制的 API 请求
"""
import requests
import json


def test_api():
    """
    测试 API 请求
    
    使用步骤：
    1. 打开 Chrome → https://create.wan.video/
    2. F12 → Network 标签 → 勾选 Preserve log
    3. 操作页面（点击作品、切换等）
    4. 找到 API 请求，右键 → Copy → Copy as cURL
    5. 把 URL、Headers 填到下面
    """
    
    print("=" * 80)
    print("API 测试工具")
    print("=" * 80)
    
    # ========== 在这里填写从浏览器复制的信息 ==========
    
    # API 地址（从 Network 面板复制）
    api_url = "https://api.wan.video/v1/explore/videos"  # 替换为真实地址
    
    # 请求方法
    method = "GET"  # 或 "POST"
    
    # Headers（从 Network 面板复制）
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://create.wan.video/',
        # 'Authorization': 'Bearer xxx',  # 如果有，从浏览器复制
        # 'Cookie': 'session=xxx',  # 如果需要
    }
    
    # GET 请求参数（如果是 GET）
    params = {
        'page': 1,
        'limit': 10,
    }
    
    # POST 请求 Body（如果是 POST）
    json_body = {
        'page': 1,
        'pageSize': 10,
    }
    
    # ========== 执行请求 ==========
    
    print(f"\n📡 测试 API: {api_url}")
    print(f"   方法: {method}\n")
    
    try:
        if method.upper() == "GET":
            response = requests.get(api_url, headers=headers, params=params, timeout=30)
        else:
            response = requests.post(api_url, headers=headers, json=json_body, timeout=30)
        
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应头: {dict(response.headers)}\n")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("=" * 80)
                print("📄 响应数据（JSON 格式）:")
                print("=" * 80)
                print(json.dumps(data, indent=2, ensure_ascii=False))
                print("=" * 80)
                
                # 分析数据结构
                print("\n📊 数据结构分析:")
                analyze_structure(data)
                
            except json.JSONDecodeError:
                print(f"⚠️  响应不是 JSON 格式:")
                print(response.text[:500])
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   响应内容: {response.text[:500]}")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
        print("\n💡 可能的原因:")
        print("   1. API 地址错误")
        print("   2. 需要认证（Authorization header）")
        print("   3. 需要 Cookie")
        print("   4. 网络问题")


def analyze_structure(data, prefix=""):
    """递归分析 JSON 结构"""
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}{key}: {type(value).__name__} (长度: {len(value)})")
                if len(value) > 0:
                    if isinstance(value, list):
                        analyze_structure(value[0], prefix + "  ")
                    else:
                        analyze_structure(value, prefix + "  ")
            else:
                value_preview = str(value)[:50]
                print(f"{prefix}{key}: {type(value).__name__} = {value_preview}")
    elif isinstance(data, list) and len(data) > 0:
        print(f"{prefix}[0]: {type(data[0]).__name__}")
        if isinstance(data[0], dict):
            analyze_structure(data[0], prefix + "  ")


def extract_urls_from_response():
    """
    从响应中提取所有 URL
    用于快速查看响应中包含哪些媒体文件
    """
    print("\n" + "=" * 80)
    print("URL 提取工具")
    print("=" * 80)
    
    # 把从 Network 面板复制的响应 JSON 粘贴到这里
    response_json = """
    {
        "data": {
            "videos": [
                {
                    "id": "123",
                    "video_url": "https://example.com/video.mp4",
                    "cover": "https://example.com/cover.jpg"
                }
            ]
        }
    }
    """
    
    try:
        data = json.loads(response_json)
        urls = []
        
        def find_urls(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.startswith('http'):
                        urls.append((key, value))
                    elif isinstance(value, (dict, list)):
                        find_urls(value)
            elif isinstance(obj, list):
                for item in obj:
                    find_urls(item)
        
        find_urls(data)
        
        print(f"\n找到 {len(urls)} 个 URL:")
        for key, url in urls:
            file_type = "图片" if any(ext in url for ext in ['.jpg', '.png', '.gif', '.webp']) else \
                       "视频" if any(ext in url for ext in ['.mp4', '.mov', '.webm']) else "其他"
            print(f"  [{file_type}] {key}: {url}")
    
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败: {e}")


if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║              API 测试工具 - 使用说明                         ║
    ║                                                              ║
    ║  功能 1: test_api()                                          ║
    ║    - 测试从浏览器复制的 API 请求                             ║
    ║    - 查看响应数据结构                                        ║
    ║                                                              ║
    ║  功能 2: extract_urls_from_response()                        ║
    ║    - 从响应 JSON 中提取所有 URL                              ║
    ║    - 快速查看包含哪些媒体文件                                ║
    ║                                                              ║
    ║  提示：修改上面的代码，填入真实的 API 信息                   ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # 执行测试
    test_api()
    
    # 如果需要提取 URL，取消下面的注释
    # extract_urls_from_response()

