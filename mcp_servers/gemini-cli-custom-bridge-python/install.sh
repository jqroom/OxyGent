#!/bin/bash

# Gemini CLI Custom Bridge Python 安装脚本

set -e

echo "🚀 开始安装 Gemini CLI Custom Bridge Python..."

# 检查 Python 版本
echo "📋 检查 Python 版本..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3。请先安装 Python 3.8 或更高版本。"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ 找到 Python $PYTHON_VERSION"

# 检查 pip
echo "📋 检查 pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌ 错误: 未找到 pip3。请先安装 pip。"
    exit 1
fi

echo "✅ 找到 pip"

# 注意：此项目使用上层OxyGent项目的虚拟环境
echo "📋 检测到上层项目虚拟环境，将使用共享依赖..."

# 安装依赖
echo "📦 安装 Python 依赖..."
pip3 install -e .

# 沙盒目录将使用上层项目的 cache_dir/gemini_cli_workspace
echo "📁 沙盒目录使用上层项目路径..."

# 复制环境变量文件
if [ ! -f ".env" ]; then
    echo "⚙️  创建环境配置文件..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请编辑其中的配置"
    echo "📝 请编辑 .env 文件并填入正确的 API 配置"
else
    echo "✅ .env 文件已存在"
fi

echo ""
echo "🎉 安装完成！"
echo ""
echo "📋 下一步："
echo "1. 编辑 .env 文件，填入正确的 API 配置"
echo "2. 运行服务器: python3 -m gemini_bridge"
echo "3. 或者使用: python3 src/gemini_bridge/__main__.py"
echo ""
echo "📖 更多信息请查看 README.md"