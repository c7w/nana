#!/bin/bash

# Paper Search Agent Rev1 启动脚本

echo "🚀 Starting Paper Search Agent Rev1..."
echo "📂 Working directory: $(pwd)"

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+ first."
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found. Please run from the correct directory."
    exit 1
fi

# 检查配置文件
if [ ! -f "../../config/config.yaml" ]; then
    echo "⚠️  Warning: config.yaml not found. Please copy from config.template.yaml and configure it."
    echo "📝 Expected location: ../../config/config.yaml"
fi

# 安装依赖（如果需要）
echo "📦 Checking dependencies..."
pip install -q -r requirements.txt

# 启动应用
echo "🌐 Starting FastAPI server on http://localhost:20002"
echo "📖 Open your browser and visit: http://localhost:20002"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

python main.py 