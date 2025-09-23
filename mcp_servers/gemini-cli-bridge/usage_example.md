# 使用示例

## 1. 在 JoyCode 中配置 MCP 服务器

将以下配置添加到你的 JoyCode 配置文件中：

```json
{
  "mcpServers": {
    "gemini-cli-bridge": {
      "command": "python",
      "args": ["-m", "src.gemini_cli_bridge"],
      "cwd": "/path/to/mcp_servers/gemini-cli-bridge"
    }
  }
}
```

## 2. 环境配置

确保 `.env` 文件包含你的 API 配置：

```bash
# 自定义 API 配置
CUSTOM_API_BASE_URL=https://your-api.example.com
CUSTOM_API_KEY=your_api_key_here
CUSTOM_MODEL_NAME=your_model_name

# 代理配置（可选）
PROXY_HOST=localhost
PROXY_PORT=8080
```

## 3. 可用工具

服务器提供以下 6 个主要工具：

- **gemini_chat**: 与 Gemini 模型进行对话
- **gemini_analyze**: 分析文本、代码或文档
- **gemini_file_ops**: 文件操作和处理
- **gemini_command**: 执行 Gemini CLI 命令
- **gemini_tools**: 访问 Gemini 的内置工具
- **gemini_custom**: 自定义功能扩展

## 4. 使用示例

```python
# 通过 MCP 调用 Gemini CLI
result = await mcp_client.call_tool("gemini_chat", {
    "message": "请帮我分析这段代码",
    "context": "这是一个 Python 函数"
})
```

## 5. 自定义 API 支持

该桥接服务器支持将 Gemini CLI 的 API 调用重定向到你的自定义接口：

- 自动拦截 Gemini CLI 的 API 请求
- 转换请求格式以适配你的 API
- 处理响应并返回给 Gemini CLI
- 支持完整的 Gemini CLI 功能集

## 6. 故障排除

如果遇到问题，请检查：

1. Python 虚拟环境是否正确激活
2. 所有依赖包是否已安装
3. `.env` 文件配置是否正确
4. Gemini CLI 是否已正确安装
5. 网络连接是否正常
