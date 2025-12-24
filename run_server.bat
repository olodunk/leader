@echo off
title 中层干部测评系统服务端
color 0a
echo 正在启动系统，请勿关闭此窗口...
echo.

:: 检查是否安装了依赖 (可选，简单跳过)
:: pip install -r requirements.txt

:: 运行 server.py
python server.py

pause