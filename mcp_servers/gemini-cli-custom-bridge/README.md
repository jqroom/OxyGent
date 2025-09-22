# Gemini CLI Custom Bridge

这是一个 MCP (Model Context Protocol) 服务器，用于将 Gemini CLI 的请求代理到项目的京东云 AI 接口。

## 功能特性

- 🔗 **API 代理**: 将 Gemini CLI 请求转发到京东云 AI API
- 🛠️ **代码分析**: 提供代码分析和理解功能
- 🔧 **项目级配置**: 配置文件和脚本集成到项目仓库中
- 👥 **团队协作**: 便于团队成员共享和部署配置

## 快速开始

### 1. 克隆和安装

```bash
# 克隆项目（如果是新环境）
git clone <repository-url>
cd <project-root>/gemini-cli-custom-bridge

# 安装依赖
npm install
```

### 2. 配置环境变量

**重要说明**: MCP 服务器会自动读取项目根目录的 `.env.local` 文件中的京东云 AI 配置。

如果项目根目录已有 `.env.local` 文件（包含 `NEXT_PUBLIC_AI_API_URL`、`NEXT_PUBLIC_AI_MODEL`、`NEXT_PUBLIC_AI_API_KEY` 等配置），则无需额外配置。

如果需要备用配置，可以复制环境变量示例文件：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置备用配置：

```env
NEXT_PUBLIC_AI_API_URL=http://ai-api.custom.com/v1
NEXT_PUBLIC_AI_MODEL=Claude-sonnet-4
```

### 3. 构建和配置

使用一键安装脚本：

```bash
npm run setup
```

或者手动执行：

```bash
# 构建项目
npm run build

# 配置 Gemini CLI
npm run configure-gemini
```

### 4. 验证配置

检查 Gemini CLI 配置是否正确：

```bash
gemini config list
```

应该能看到 MCP 服务器配置已添加。

## 项目启动流程

### 首次部署（新环境）

1. **克隆仓库**

   ```bash
   git clone <repository-url>
   cd <project-root>/gemini-cli-custom-bridge
   ```

2. **安装依赖**

   ```bash
   npm install
   ```

3. **配置环境**

   ```bash
   cp .env.example .env
   # 编辑 .env 文件设置正确的 API 地址
   ```

4. **一键配置**
   ```bash
   npm run setup
   ```

### 日常使用

项目配置完成后，Gemini CLI 会自动使用配置的 MCP 服务器。无需手动启动服务器，Gemini CLI 会在需要时自动启动。

```bash
# 直接使用 Gemini CLI
gemini ask "解释这段代码的功能"
gemini analyze-code --file src/index.js
```

### 更新配置

当项目配置有更新时：

```bash
# 拉取最新代码
git pull

# 重新安装依赖（如果 package.json 有变化）
npm install

# 重新构建和配置
npm run setup
```

## 可用脚本

- `npm run build` - 构建 TypeScript 项目
- `npm run start` - 启动 MCP 服务器
- `npm run dev` - 开发模式运行
- `npm run configure-gemini` - 配置 Gemini CLI 使用此 MCP 服务器
- `npm run setup` - 一键构建和配置

## 工具说明

### chat_completion

与京东云 AI 进行对话交互。

**参数:**

- `messages` (必需): 对话消息数组
- `model` (可选): AI 模型名称，默认为 "gpt-3.5-turbo"
- `temperature` (可选): 温度参数，默认为 0.7
- `max_tokens` (可选): 最大令牌数，默认为 1000

**示例:**

```bash
gemini ask "解释一下这段代码的功能"
```

### analyze_code

分析代码文件或代码片段。

**参数:**

- `code` (必需): 要分析的代码内容
- `language` (可选): 编程语言，默认为 "javascript"
- `analysis_type` (可选): 分析类型，默认为 "general"

**示例:**

```bash
gemini analyze-code --file src/index.js
```

## 项目结构

```
gemini-cli-custom-bridge/
├── src/
│   ├── index.ts          # MCP 服务器主文件
│   └── types.ts          # TypeScript 类型定义
├── scripts/
│   └── configure-gemini.js  # Gemini CLI 配置脚本
├── dist/                 # 构建输出目录
├── .env.example          # 环境变量示例
├── gemini-settings.json  # Gemini CLI 配置模板
├── setup.sh             # 一键安装脚本
├── package.json
├── tsconfig.json
└── README.md
```

## 配置文件说明

### gemini-settings.json

这是 Gemini CLI 的配置模板，包含了 MCP 服务器的配置信息：

```json
{
  "mcpServers": {
    "custom-bridge": {
      "command": "node",
      "args": ["dist/index.js"],
      "cwd": "/path/to/gemini-cli-custom-bridge"
    }
  }
}
```

### 环境变量

**配置优先级**:

1. **项目根目录 `.env.local`** (优先使用)

   - `NEXT_PUBLIC_AI_API_URL`: 京东云 AI API 的完整 URL
   - `NEXT_PUBLIC_AI_MODEL`: AI 模型名称
   - `NEXT_PUBLIC_AI_API_KEY`: API 密钥

2. **本地 `.env` 文件** (备用配置)
   - `NEXT_PUBLIC_AI_API_URL`: 京东云 AI API 的基础 URL
   - `NEXT_PUBLIC_AI_MODEL`: 默认 AI 模型
   - `NEXT_PUBLIC_AI_API_KEY`: API 密钥（如果需要）

MCP 服务器会自动检测并使用项目根目录的 `.env.local` 配置，如果不存在则使用本地 `.env` 配置作为备用。

## 团队协作

### 版本控制说明

项目已配置 `.gitignore` 文件，会自动忽略：

- `node_modules/` - 依赖包目录
- `dist/` - 构建输出目录
- `.env` - 环境变量文件（包含敏感信息）
- 其他临时文件和 IDE 配置

这确保了仓库只包含源代码和配置模板，不包含依赖和敏感信息。

### 新成员加入

1. **克隆项目仓库**

   ```bash
   git clone <repository-url>
   cd <project-root>/gemini-cli-custom-bridge
   ```

2. **安装依赖**

   ```bash
   npm install
   ```

3. **配置环境变量**

   如果项目根目录已有 `.env.local` 文件，则无需额外配置。

   如果需要备用配置：

   ```bash
   cp .env.example .env
   # 编辑 .env 文件，设置备用 API 地址
   ```

4. **一键配置**
   ```bash
   npm run setup
   ```

### 配置更新流程

当项目配置需要更新时：

1. **开发者更新配置**

   ```bash
   # 修改相关配置文件（如 package.json, src/*, scripts/* 等）
   git add .
   git commit -m "更新 MCP 服务器配置"
   git push
   ```

2. **团队成员同步更新**

   ```bash
   # 拉取最新代码
   git pull

   # 如果 package.json 有变化，重新安装依赖
   npm install

   # 重新构建和配置
   npm run setup
   ```

### 环境变量管理

**配置优先级**:

1. **项目根目录 `.env.local`** - 主要配置，包含京东云 AI 相关设置
2. **本地 `.env` 文件** - 备用配置，用于本地开发或测试

**管理原则**:

- MCP 服务器会自动读取项目根目录的 `.env.local` 文件
- 如果项目根目录没有 `.env.local`，则使用本地 `.env` 作为备用
- `.env.example` 文件包含备用配置的模板
- 不要将 `.env` 文件提交到版本控制系统
- 项目根目录的 `.env.local` 由项目主配置管理，通常已存在
- 如需添加新的备用环境变量，请更新 `.env.example` 文件

## 故障排除

### 常见问题

1. **MCP 服务器无法启动**

   - 检查 Node.js 版本是否 >= 18
   - 确保已运行 `npm run build`
   - 检查环境变量配置

2. **Gemini CLI 无法连接**

   - 验证 Gemini CLI 配置: `gemini config list`
   - 检查 MCP 服务器路径是否正确
   - 确保项目已构建

3. **API 调用失败**
   - 首先检查项目根目录的 `.env.local` 文件中的京东云 AI 配置
   - 如果没有 `.env.local`，检查本地 `.env` 文件中的 API 地址
   - 确认京东云 AI 服务正在运行
   - 检查网络连接
   - 验证 API 密钥是否正确

### 调试模式

启用调试模式查看详细日志：

```bash
DEBUG=* npm run start
```

## 技术架构

- **MCP Protocol**: 使用标准的 Model Context Protocol 进行通信
- **TypeScript**: 提供类型安全和更好的开发体验
- **Node.js**: 运行时环境
- **京东云 AI**: 后端 AI 服务提供商

## 许可证

MIT License
