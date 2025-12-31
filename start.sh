#!/bin/bash
# 一键启动脚本

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行："
    echo "   ./install_macos.sh"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 运行程序
python3 main.py "$@"

# 保存退出码
EXIT_CODE=$?

# 退出虚拟环境
deactivate

# 返回退出码
exit $EXIT_CODE


