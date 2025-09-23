# Gemini CLI Bridge MCP Server

一个基于原版 Google Gemini CLI 的 MCP (Model Context Protocol) 桥接服务器，支持自定义 API 接口配置。

## 🚀 功能特性

### 核心能力

- **完整 Gemini CLI 功能**: 直接调用原版 gemini-cli，获得所有内置工具和功能
- **自定义 API 支持**: 支持配置自定义 AI API 接口，而非仅限于 Google Gemini API
- **MCP 协议兼容**: 作为 MCP 服务器，可与支持 MCP 的客户端集成
- **配置灵活**: 支持多种配置方式（环境变量、配置文件、命令行参数）

### Gemini CLI 原生功能

通过桥接调用，您可以使用 Gemini CLI 的所有功能：

- 代码分析和生成
- 文件操作和管理
- 命令执行
- 项目理解和重构
- 内置工具集
- MCP 服务器扩展支持
- GitHub 集成
- 自定义工具开发

## 📋 系统要求

- Node.js 18+ (用于运行 gemini-cli)
- Python 3.8+ (用于 MCP 桥接服务器)
- npm/yarn (用于安装 gemini-cli)

## 🛠️ 安装

### 1. 安装 Gemini CLI

```bash
# 全局安装 gemini-cli
npm install -g @google/gemini-cli

# 验证安装
gemini --version
```

### 2. 安装 MCP 桥接服务器

```bash
# 进入项目目录
cd mcp_servers/gemini-cli-bridge

# 安装 Python 依赖
pip install -e .

# 或者使用安装脚本
./install.sh
```

## ⚙️ 配置

### 环境变量配置

创建 `.env` 文件：

```env
# 自定义 AI API 配置
CUSTOM_AI_API_URL=http://llm-32b.jd.com/v1/chat/completions
CUSTOM_AI_MODEL=qwen25-32b-native
CUSTOM_AI_API_KEY=your-api-key-here

# Gemini CLI 配置
GEMINI_CLI_PATH=gemini  # gemini-cli 命令路径
GEMINI_CLI_WORKSPACE=./workspace  # 工作目录

# 可选配置
BRIDGE_LOG_LEVEL=INFO
BRIDGE_TIMEOUT=60
```

### Gemini CLI 配置

桥接服务器会自动为 gemini-cli 生成配置，支持：

- 自定义 API 端点配置
- settings.json 动态生成
- 环境变量传递
- 工作目录管理

## 🚀 运行

```bash
# 启动 MCP 桥接服务器
python -m gemini_cli_bridge

# 或者
python src/gemini_cli_bridge/__main__.py
```

## 📖 使用说明

### MCP 工具

桥接服务器提供以下工具，直接调用 gemini-cli：

1. **gemini_chat** - 与 AI 对话
2. **gemini_analyze** - 代码分析
3. **gemini_file_ops** - 文件操作
4. **gemini_command** - 执行命令
5. **gemini_tools** - 使用内置工具
6. **gemini_custom** - 自定义操作

### 自定义 API 集成

桥接服务器会：

1. 拦截 gemini-cli 的 API 调用
2. 将请求转发到您的自定义 API
3. 处理响应格式转换
4. 保持 gemini-cli 的完整功能

### 配置示例

#### 使用京东云 API

```env
CUSTOM_AI_API_URL=http://llm-32b.jd.com/v1/chat/completions
CUSTOM_AI_MODEL=qwen25-32b-native
CUSTOM_AI_API_KEY=your-jd-api-key
```

#### 使用其他 OpenAI 兼容 API

```env
CUSTOM_AI_API_URL=https://api.your-provider.com/v1/chat/completions
CUSTOM_AI_MODEL=your-model-name
CUSTOM_AI_API_KEY=your-api-key
```

## 🏗️ 架构设计

```
MCP 客户端 → MCP 桥接服务器 → Gemini CLI → 自定义 API
                ↓
          配置管理 & API 代理
```

### 核心组件

- **MCP 服务器**: 处理 MCP 协议通信
- **Gemini CLI 包装器**: 管理 gemini-cli 进程和配置
- **API 代理**: 拦截和重定向 API 调用
- **配置管理器**: 动态生成 gemini-cli 配置

## 🔧 开发

### 项目结构

```
mcp_servers/gemini-cli-bridge/
├── src/gemini_cli_bridge/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py          # MCP 服务器
│   ├── gemini_wrapper.py  # Gemini CLI 包装器
│   ├── api_proxy.py       # API 代理
│   ├── config_manager.py  # 配置管理
│   └── types.py           # 类型定义
├── workspace/             # Gemini CLI 工作目录
├── .env.example
├── pyproject.toml
├── install.sh
└── README.md
```

## 🐛 故障排除

### 常见问题

1. **Gemini CLI 未找到**

   ```bash
   # 检查 gemini-cli 是否正确安装
   which gemini
   gemini --version
   ```

2. **API 配置错误**

   ```bash
   # 检查环境变量
   echo $CUSTOM_AI_API_URL
   ```

3. **权限问题**
   ```bash
   # 确保工作目录权限
   chmod 755 workspace/
   ```

## 📄 许可证

本项目遵循 MIT 许可证。

---

**注意**: 此项目是 Gemini CLI 的 MCP 桥接实现，需要先安装原版 gemini-cli。
