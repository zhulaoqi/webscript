@echo off
REM 运行脚本 - Windows

echo ================================
echo AI视频素材爬虫
echo ================================
echo.

REM 检查Python
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未找到Python
    pause
    exit /b 1
)

REM 检查依赖
echo 检查依赖...
python -c "import selenium, requests, bs4" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 正在安装依赖...
    pip install -r requirements.txt
)

REM 运行主程序
echo.
echo 开始运行...
echo.
python main.py %*

echo.
echo 完成！
pause


