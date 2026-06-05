#!/bin/bash
cd "$(dirname "$0")"

echo "🔧 安装 Python 依赖..."
pip3 install flask flask-cors requests -q

echo "🚀 启动单位换算工具..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  访问地址: http://localhost:5000"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 backend/app.py
