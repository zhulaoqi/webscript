"""
配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 代理配置
PROXY_CONFIG = {
    'host': os.getenv('PROXY_HOST', ''),
    'user': os.getenv('PROXY_USER', ''),
    'password': os.getenv('PROXY_PASSWORD', ''),
    'port': os.getenv('PROXY_PORT', ''),
}

# 下载配置
DOWNLOAD_CONFIG = {
    'delay_min': int(os.getenv('DOWNLOAD_DELAY_MIN', 2)),
    'delay_max': int(os.getenv('DOWNLOAD_DELAY_MAX', 5)),
    'max_retries': int(os.getenv('MAX_RETRIES', 3)),
    'timeout': int(os.getenv('TIMEOUT', 30)),
}

# 输出配置
OUTPUT_DIR = os.getenv('OUTPUT_DIR', './downloads')

# 网站配置
WEBSITES = {
    'wan_video': {
        'url': 'https://create.wan.video/',
        'target_count': 50,
        'types': ['text2video', 'image2video']
    },
    'higgsfield': {
        'url': 'https://higgsfield.ai/',
        'target_count': 50,  # 每个网站50个素材
        'categories': [
            'Kling 2.5 Turbo',
            'Camera Controls',
            'Viral',
            'Commercial',
            'UGC',
            'Sora 2 Community',
            'Wan 2.5 Community'
        ]
    },
    'imagine_art': {
        'url': 'https://www.imagine.art/community',  # 改为community页面
        'target_count': 50,  # 每个网站50个素材
    },
    'invideo': {
        'url': 'https://invideo.io/ideas',
        'target_count': 50,  # 每个网站50个素材
        'categories': [
            'Million Dollar Ads',
            'UGC & Avatars'
        ]
    },
    'pixverse': {
        'url': 'https://app.pixverse.ai/onboard',
        'target_count': 20,  # 每个类别20个素材 (总共7个类别 = 140个)
        'categories': [
            'Winter Vibe',
            'Ad Magic',
            'Cinematic Narrative',
            'Stylistic Art',
            'Animal Theatre',
            'Effects Rendering',
            'Emotional Close-up'
        ]
    }
}

# User-Agent列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
]

# AWS S3配置
AWS_S3_CONFIG = {
    'url_prefix': 'https://ad-pex-test-cdn.adpexai.com/',
    'original_url': 'https://ad-pex-test.s3.ap-southeast-1.amazonaws.com/',
    'bucket_name': 'ad-pex-test',
    'access_key_id': 'AKIAVIPDWYOL5LMWTRVD',
    'secret_access_key': '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',
    'region': 'ap-southeast-1',
    'accelerate_url': 'https://s3-accelerate.amazonaws.com',
}

