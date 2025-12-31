# AI视频素材爬虫

从5个AI视频生成平台批量采集视频素材的Python工具。

## 🎯 功能特点

- 🎬 支持5个主流AI视频平台（Wan Video、Higgsfield、Imagine.art、InVideo、Pixverse）
- 📦 自动下载视频、缩略图、原图和提示词
- 💾 导出JSON和Excel格式数据
- 📁 自动创建ZIP压缩包
- 🔄 智能延迟和重试机制
- 🌐 支持代理配置

## 支持的网站

| 网站 | URL | 目标数量 | 类型 |
|------|-----|---------|------|
| Wan Video | https://create.wan.video/ | 50条 | 文生视频 + 图生视频 |
| Higgsfield | https://higgsfield.ai/ | 7个分类，每个20条 | 文生视频 |
| Imagine.art | https://www.imagine.art/video | 50条 | 文生视频 |
| InVideo | https://invideo.io/ideas | 2个分类，每个20条 | 文生视频 |
| Pixverse | https://app.pixverse.ai/onboard | 7个分类，每个20条 | 文生视频 |

**总计目标：**
- 文生视频：约200条
- 图生视频：约200条

## 💻 系统要求

- Python 3.8+
- macOS / Windows / Linux

## 🔧 技术方案

本项目采用**纯 HTTP 请求**方式，不依赖浏览器自动化（Selenium/Playwright）：

**优势：**
- ✅ 更稳定 - 直接调用后端 API，不受页面 DOM 变化影响
- ✅ 更快速 - 无需等待页面渲染
- ✅ 更准确 - 获取完整的 JSON 数据，包含所有字段
- ✅ 更轻量 - 不需要 Chrome、ChromeDriver

**工作流程：**
1. 手动打开浏览器 F12 → Network 标签
2. 操作页面，找到真实的 API 请求
3. 复制 API URL、Headers、参数
4. 配置到 scraper 中
5. 用 requests 直接调用 API

## 📦 安装

### macOS（推荐：一键安装）

```bash
# 进入项目目录
cd /Users/zhujinqi/Documents/pyCode/webScript

# 运行安装脚本
./install_macos.sh
```

安装脚本会自动：
- ✅ 创建虚拟环境（避免系统污染）
- ✅ 安装所有依赖
- ✅ 验证安装
- ✅ 配置环境

### Windows

```bash
# 双击运行
run.bat

# 或手动安装
pip install -r requirements.txt
```

### Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 配置代理（可选）

如需使用代理，编辑 `.env` 文件：

```ini
PROXY_HOST=your-proxy-host
PROXY_USER=your-username
PROXY_PASSWORD=your-password
```

## 🚀 使用方法

### macOS（一键启动）

```bash
# 爬取所有网站（自动上传S3并生成Excel）
./start.sh

# 指定网站
./start.sh --sites wan higgsfield

# 自定义输出
./start.sh --output ./my_videos
```

**自动功能：**
- ✅ 下载视频、图片
- ✅ 自动上传到AWS S3
- ✅ 生成Excel文件（包含S3链接）
- ✅ 不生成JSON、ZIP等多余文件

### Windows

```bash
# 双击运行
run.bat

# 或命令行
python main.py
python main.py --sites wan
```

### Linux

```bash
source venv/bin/activate
python3 main.py
```

### 可选网站

- `wan` - Wan Video（文生+图生视频）
- `higgsfield` - Higgsfield.ai
- `imagine` - Imagine.art
- `invideo` - InVideo.io
- `pixverse` - Pixverse.ai
- `all` - 全部（默认）

## 📂 输出说明

程序运行后会生成：

1. **Excel文件** - 包含所有视频的S3链接
   - 格式：`video_materials_YYYYMMDD_HHMMSS.xlsx`
   - 包含列：type、名称、file_s3_cloud_url、file_thumbnail_s3_cloud_url、source_image_s3_url、prompt、remark

2. **临时下载文件** - 在 `downloads/` 目录
   - 用于上传到S3后可以删除

3. **S3存储** - 所有文件上传到AWS S3
   - CDN地址：`https://ad-pex-test-cdn.adpexai.com/`
   - 路径格式：`video-materials/{分类}/{文件名}`

## 📊 Excel数据格式

生成的Excel包含以下列：

| 列名 | 说明 | 示例 |
|-----|------|-----|
| type | 类型 | text2video / image2video |
| 名称 | 分类名称 | Higgsfield - Kling 2.5 Turbo |
| file_s3_cloud_url | 视频S3链接 | https://ad-pex-test-cdn.adpexai.com/... |
| file_thumbnail_s3_cloud_url | 缩略图S3链接 | https://ad-pex-test-cdn.adpexai.com/... |
| source_image_s3_url | 原图S3链接 | https://ad-pex-test-cdn.adpexai.com/... |
| prompt | 提示词 | A beautiful sunset over mountains |
| remark | 备注JSON | {"route":"...", "prompt":"..."} |

## 项目结构

```
webScript/
├── main.py                     # 主程序
├── config.py                   # 配置文件
├── utils.py                    # 工具函数
├── requirements.txt            # 依赖列表
├── .env.example               # 环境变量示例
├── README.md                   # 本文档
└── scrapers/                   # 爬虫模块
    ├── __init__.py
    ├── base_scraper.py         # 基础爬虫类
    ├── wan_video_scraper.py    # Wan Video爬虫
    ├── higgsfield_scraper.py   # Higgsfield爬虫
    ├── imagine_art_scraper.py  # Imagine.art爬虫
    ├── invideo_scraper.py      # InVideo爬虫
    └── pixverse_scraper.py     # Pixverse爬虫
```

## 注意事项

### 代理配置

部分网站可能需要海外代理访问。配置方法：

1. 编辑 `.env` 文件
2. 设置代理参数：
   ```ini
   PROXY_HOST=魔戒.net
   PROXY_USER=1587349659@qq.com
   PROXY_PASSWORD=670404CDMcdm
   ```

### 浏览器驱动

本工具使用Selenium和Chrome浏览器：

- 自动下载ChromeDriver（通过webdriver-manager）
- 需要安装Chrome浏览器
- 运行在无头模式（headless）

### 下载限制

- 自动随机延迟（2-5秒）防止被封
- 失败自动重试（最多3次）
- 分散下载，避免集中请求

### 法律声明

- 仅用于学习和研究目的
- 请遵守各网站的使用条款
- 不要过度爬取，避免给服务器造成压力
- 下载的内容版权归原作者所有

## ❓ 常见问题

### macOS提示"externally-managed-environment"？

这是Python 3.11+的安全特性，解决方法：
```bash
./install_macos.sh  # 会自动创建虚拟环境
```

### ChromeDriver下载失败？

1. 配置代理（编辑 `.env` 文件）
2. 或等待几分钟自动重试

### 网站爬取失败？

1. 检查网络连接
2. 配置代理
3. 等待后重试（可能是临时限制）

### 如何调试？

编辑 `scrapers/base_scraper.py`，注释掉：
```python
# chrome_options.add_argument('--headless')
```

### 下载慢怎么办？

编辑 `.env` 文件：
```ini
DOWNLOAD_DELAY_MIN=1
DOWNLOAD_DELAY_MAX=2
```

## ⚠️ 重要提示

- 仅供学习和研究使用
- 遵守各网站使用条款
- 合理使用，避免滥用
- 视频版权归原作者所有

## 📄 许可

MIT License

---

**完整安装和使用指南请查看 `一键安装.txt`**

