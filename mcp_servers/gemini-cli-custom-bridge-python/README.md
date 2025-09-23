# Gemini CLI Custom Bridge Python

一个基于 Python 的 MCP (Model Context Protocol) 服务器，用于将 Gemini CLI 的请求代理到自定义 AI 接口。这是 TypeScript 版本的完整 Python 重写版本。

## 🚀 功能特性

### 核心功能

- **AI 聊天完成**: 支持流式和非流式 AI 对话
- **代码分析**: 智能代码分析和建议
- **文件操作**: 安全的文件读取、写入和列表功能
- **命令执行**: 受限的安全命令执行
- **路径安全管理**: 严格限制在指定目录内操作

### 扩展工具

- **grep**: 文件内容搜索
- **glob**: 文件模式匹配
- **edit**: 文件编辑操作
- **web_fetch**: 网页内容获取
- **web_search**: 网络搜索（需要配置搜索 API）
- **memory**: 持久化内存操作

### 安全特性

- 路径验证和沙盒限制
- 危险命令检查
- 文件大小限制
- 超时控制
- 错误处理和日志记录

## 📋 系统要求

- Python 3.8 或更高版本
- pip 包管理器
- 自定义 AI API 访问权限

## 🛠️ 安装

### 自动安装（推荐）

```bash
# 克隆或下载项目后，在项目目录中运行：
./install.sh
```

### 手动安装

```bash
# 1. 创建虚拟环境（可选但推荐）
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -e .

# 3. 创建配置文件
cp .env.example .env

# 4. 创建临时目录
mkdir -p temp
```

## ⚙️ 配置

### 环境变量配置

编辑 `.env` 文件，填入以下必要配置：

```env
# 自定义 AI API 配置（必填）
NEXT_PUBLIC_AI_API_URL=https://your-ai-api-endpoint.com
NEXT_PUBLIC_AI_MODEL=your-model-name
NEXT_PUBLIC_AI_API_KEY=your-api-key-here

# 可选配置
GEMINI_BRIDGE_LOG_LEVEL=INFO
GEMINI_BRIDGE_TIMEOUT=30
GEMINI_BRIDGE_MAX_RETRIES=3
```

### 配置说明

- `NEXT_PUBLIC_AI_API_URL`: 自定义 AI API 的完整 URL
- `NEXT_PUBLIC_AI_MODEL`: 要使用的 AI 模型名称
- `NEXT_PUBLIC_AI_API_KEY`: API 访问密钥
- `GEMINI_BRIDGE_LOG_LEVEL`: 日志级别（DEBUG, INFO, WARNING, ERROR）
- `GEMINI_BRIDGE_TIMEOUT`: 请求超时时间（秒）
- `GEMINI_BRIDGE_MAX_RETRIES`: 最大重试次数

## 🚀 运行

### 方式一：作为模块运行

```bash
python3 -m gemini_bridge
```

### 方式二：直接运行

```bash
python3 src/gemini_bridge/__main__.py
```

### 方式三：在虚拟环境中运行

```bash
source venv/bin/activate
python3 -m gemini_bridge
```

## 📖 使用说明

### MCP 工具列表

服务器提供以下 13 个工具：

1. **chat_completion** - AI 聊天完成
2. **analyze_code** - 代码分析
3. **read_file** - 读取文件
4. **write_file** - 写入文件
5. **list_files** - 列出文件
6. **execute_command** - 执行命令
7. **read_many_files** - 批量读取文件
8. **grep** - 文件搜索
9. **glob** - 模式匹配
10. **edit** - 文件编辑
11. **web_fetch** - 网页获取
12. **web_search** - 网络搜索
13. **memory** - 内存操作

### 工作目录

- 所有文件操作都限制在 `temp/` 目录内
- 相对路径会自动解析为相对于 `temp/` 目录
- 绝对路径必须在允许的范围内

### 安全限制

- 文件操作仅限于项目的 `temp` 目录
- 命令执行有严格的安全检查
- 危险命令（如 `rm -rf`, `sudo` 等）被禁止
- 所有操作都有超时限制

## 🏗️ 项目结构

```
mcp_servers/gemini-cli-custom-bridge-python/
├── src/gemini_bridge/          # 主要源代码
│   ├── __init__.py            # 包初始化
│   ├── __main__.py            # 主入口
│   ├── server.py              # MCP 服务器
│   ├── config.py              # 配置管理
│   ├── types.py               # 类型定义
│   ├── path_manager.py        # 路径管理
│   ├── ai_client.py           # AI 客户端
│   ├── file_operations.py     # 文件操作
│   ├── command_executor.py    # 命令执行
│   └── extended_tools.py      # 扩展工具
├── temp/                      # 工作目录
├── pyproject.toml            # 项目配置
├── .env.example              # 环境变量示例
├── install.sh                # 安装脚本
└── README.md                 # 项目文档
```

## 🔧 开发

### 依赖说明

主要依赖包：

- `mcp`: MCP 协议实现
- `httpx`: HTTP 客户端
- `pydantic`: 数据验证
- `python-dotenv`: 环境变量管理
- `aiofiles`: 异步文件操作

### 扩展开发

要添加新的工具，需要：

1. 在 `types.py` 中定义参数和返回类型
2. 在相应的模块中实现工具逻辑
3. 在 `server.py` 中注册工具
4. 更新文档

## 🐛 故障排除

### 常见问题

1. **导入错误**

   ```bash
   # 确保在正确的目录中运行
   cd mcp_servers/gemini-cli-custom-bridge-python
   python3 -m gemini_bridge
   ```

2. **API 配置错误**

   ```bash
   # 检查 .env 文件是否存在且配置正确
   cat .env
   ```

3. **权限错误**

   ```bash
   # 确保 temp 目录存在且有写权限
   mkdir -p temp
   chmod 755 temp
   ```

4. **依赖问题**
   ```bash
   # 重新安装依赖
   pip install -e . --force-reinstall
   ```

### 日志调试

设置环境变量启用详细日志：

```bash
export GEMINI_BRIDGE_LOG_LEVEL=DEBUG
python3 -m gemini_bridge
```

## 📄 许可证

本项目基于原 TypeScript 版本开发，遵循相同的许可证条款。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📞 支持

如果遇到问题，请：

1. 检查本文档的故障排除部分
2. 查看项目 Issues
3. 提交新的 Issue 描述问题

---

**注意**: 这是 TypeScript 版本 `gemini-cli-custom-bridge` 的 Python 重写版本，功能完全对等。
