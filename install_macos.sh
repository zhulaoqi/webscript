#!/bin/bash
# macOS AI视频素材爬虫 - 一键安装脚本（支持指定Python版本 + 加速版）

TARGET_PYTHON_VERSION="3.11.9"

echo "================================"
echo "AI视频素材爬虫 - 安装向导"
echo "================================"
echo ""

# 1️⃣ 检查Python3
echo "1. 检查Python3..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "   ✓ 已安装 Python: $PYTHON_VERSION"

    if [[ "$PYTHON_VERSION" != "$TARGET_PYTHON_VERSION"* ]]; then
        echo "   ⚠️ 当前 Python 版本不是 $TARGET_PYTHON_VERSION，可能导致依赖安装失败"
        echo "   建议使用 pyenv 安装指定版本："
        echo "     brew install pyenv"
        echo "     pyenv install $TARGET_PYTHON_VERSION"
        echo "     pyenv local $TARGET_PYTHON_VERSION"
        echo "   按 Enter 继续使用当前 Python..."
        read
    fi
else
    echo "   ✗ 未找到 Python3"
    echo "请先安装 Python3 或使用 pyenv 安装版本 $TARGET_PYTHON_VERSION："
    echo "  brew install pyenv"
    echo "  pyenv install $TARGET_PYTHON_VERSION"
    exit 1
fi

# 2️⃣ 检查Chrome浏览器
echo ""
echo "2. 检查Chrome浏览器..."
if [ -d "/Applications/Google Chrome.app" ]; then
    echo "   ✓ Chrome已安装"
else
    echo "   ⚠️  未找到Chrome浏览器"
    echo "   请访问 https://www.google.com/chrome/ 下载安装"
    echo "   按Enter继续..."
    read
fi

# 3️⃣ 创建虚拟环境
echo ""
echo "3. 创建虚拟环境..."
if [ -d "venv" ]; then
    echo "   ✓ 虚拟环境已存在"
else
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo "   ✓ 虚拟环境创建成功"
    else
        echo "   ✗ 虚拟环境创建失败"
        exit 1
    fi
fi

# 4️⃣ 激活虚拟环境
echo ""
echo "4. 激活虚拟环境..."
source venv/bin/activate

# 5️⃣ 升级 pip, setuptools, wheel
echo ""
echo "5. 升级 pip、setuptools、wheel..."
python -m pip install --upgrade pip setuptools wheel -i https://pypi.tuna.tsinghua.edu.cn/simple

# 6️⃣ 安装依赖
echo ""
echo "6. 安装依赖包（使用国内镜像加速，可能需要几分钟）..."
python -m pip install --prefer-binary -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

if [ $? -ne 0 ]; then
    echo "   ⚠️ 安装失败，请检查网络或依赖版本"
    deactivate
    exit 1
fi
echo "   ✓ 依赖安装完成"

# 7️⃣ 验证安装
echo ""
echo "7. 验证关键依赖..."
python -c "import selenium, requests, bs4, pandas" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "   ✓ 验证通过"
else
    echo "   ✗ 验证失败，请检查 requirements.txt"
    deactivate
    exit 1
fi

# 8️⃣ 设置执行权限
echo ""
echo "8. 设置权限..."
chmod +x start.sh 2>/dev/null
echo "   ✓ 完成"

# 9️⃣ 创建 .env 文件
echo ""
echo "9. 创建配置文件..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "   ✓ 已创建 .env 文件（如需代理请编辑）"
    fi
else
    echo "   ✓ .env 已存在"
fi

# 10️⃣ 退出虚拟环境
deactivate

echo ""
echo "================================"
echo "✓ 安装完成！"
echo "================================"
echo ""
echo "🚀 启动项目："
echo "  source venv/bin/activate"
echo "  ./start.sh"
echo ""
echo "📖 更多用法见 README.md"
echo ""
