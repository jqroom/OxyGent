#!/bin/bash

# Gemini CLI Custom AI Bridge 安装脚本

echo "🚀 开始安装 Gemini CLI Custom AI Bridge..."

# 检查 Node.js 是否安装
if ! command -v node &> /dev/null; then
    echo "❌ 错误: 未找到 Node.js，请先安装 Node.js"
    exit 1
fi

# 检查 npm 是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ 错误: 未找到 npm，请先安装 npm"
    exit 1
fi

echo "✅ Node.js 和 npm 已安装"

# 安装依赖
echo "📦 安装依赖包..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ 依赖安装失败"
    exit 1
fi

echo "✅ 依赖安装成功"

# 创建环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp ../.env.local .env
    echo "✅ 已创建 .env 文件，请根据需要修改配置"
else
    echo "ℹ️  .env 文件已存在，跳过创建"
fi

# 构建项目
echo "🔨 构建项目..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ 项目构建失败"
    exit 1
fi

echo "✅ 项目构建成功"

# 获取当前目录的绝对路径
CURRENT_DIR=$(pwd)
BRIDGE_PATH="$CURRENT_DIR/dist/index.js"

# 创建 Gemini CLI 配置目录
GEMINI_CONFIG_DIR="$HOME/.gemini"
GEMINI_CONFIG_FILE="$GEMINI_CONFIG_DIR/settings.json"

echo "📁 配置 Gemini CLI..."

# 创建配置目录
mkdir -p "$GEMINI_CONFIG_DIR"

# 检查是否已有配置文件
if [ -f "$GEMINI_CONFIG_FILE" ]; then
    echo "⚠️  检测到现有的 Gemini CLI 配置文件"
    echo "📄 备份现有配置到 settings.json.backup"
    cp "$GEMINI_CONFIG_FILE" "$GEMINI_CONFIG_FILE.backup"
fi

# 创建新的配置文件
cat > "$GEMINI_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "custom-ai-bridge": {
      "command": "node",
      "args": ["$BRIDGE_PATH"],
      "env": {
        "NEXT_PUBLIC_AI_API_URL": "http://ai-api.custom.com/v1",
        "NEXT_PUBLIC_AI_MODEL": "Claude-sonnet-4",
        "NEXT_PUBLIC_AI_API_KEY": "pk-a5301c53-f5f1-4475-b096-f7a8497b35d5"
      }
    }
  },
  "model": "Claude-sonnet-4",
  "systemPrompt": "你现在可以通过 custom-ai-bridge MCP 服务器访问京东云 AI 功能。使用 chat_completion 工具进行对话，使用 analyze_code 工具分析代码。",
  "temperature": 0.7,
  "maxTokens": 20000
}
EOF

echo "✅ Gemini CLI 配置完成"

echo ""
echo "🎉 安装完成！"
echo ""
echo "📋 下一步操作："
echo "1. 确保你的京东云 AI 服务正在运行 (http://localhost:3000)"
echo "2. 根据需要修改 .env 文件中的配置"
echo "3. 启动 Gemini CLI: gemini"
echo ""
echo "🔧 配置文件位置:"
echo "   - MCP 服务器: $BRIDGE_PATH"
echo "   - Gemini CLI 配置: $GEMINI_CONFIG_FILE"
echo "   - 环境变量: $CURRENT_DIR/.env"
echo ""
echo "📚 更多信息请查看 README.md"