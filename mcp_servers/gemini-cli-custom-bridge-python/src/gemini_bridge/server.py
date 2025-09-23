"""
MCP 服务器主要实现
基于 Python MCP SDK 实现的 Gemini CLI Custom Bridge 服务器
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, Sequence

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource
)
import mcp.types as types
from pydantic import AnyUrl

from .config import get_server_config, validate_config, print_config_info
from .types import (
    ToolResult,
    ChatCompletionArgs,
    CodeAnalysisArgs,
    ReadFileArgs,
    WriteFileArgs,
    ListFilesArgs,
    ReadManyFilesArgs,
    ExecuteCommandArgs,
    GrepArgs,
    GlobArgs,
    EditArgs,
    WebFetchArgs,
    WebSearchArgs,
    MemoryArgs
)
from .ai_client import AIClient
from .file_operations import FileOperations
from .command_executor import CommandExecutor
from .extended_tools import ExtendedTools


class GeminiBridgeServer:
    """Gemini Bridge MCP 服务器"""
    
    def __init__(self):
        self.server = Server("gemini-cli-custom-bridge-python")
        self.config = get_server_config()
        self.ai_client = AIClient()
        self.file_ops = FileOperations()
        self.command_executor = CommandExecutor()
        self.extended_tools = ExtendedTools()
        
        # 注册工具和资源
        self._register_tools()
        self._register_resources()
        
        print("[SERVER] Gemini Bridge MCP 服务器初始化完成", file=sys.stderr)
    
    def _register_tools(self):
        """注册所有工具"""
        
        # 工具列表处理程序
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """列出所有可用工具"""
            return [
                types.Tool(
                    name="chat_completion",
                    description="AI 聊天完成 - 发送消息给 AI 并获取回复",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "messages": {"type": "array", "description": "聊天消息数组"},
                            "temperature": {"type": "number", "description": "温度参数", "default": 0.7},
                            "max_tokens": {"type": "integer", "description": "最大令牌数", "default": 2000}
                        },
                        "required": ["messages"]
                    }
                ),
                types.Tool(
                    name="analyze_code",
                    description="代码分析 - 分析代码质量、结构和潜在问题",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "要分析的代码"},
                            "language": {"type": "string", "description": "编程语言", "default": "auto"},
                            "analysis_type": {"type": "string", "description": "分析类型", "default": "comprehensive"}
                        },
                        "required": ["code"]
                    }
                ),
                types.Tool(
                    name="read_file",
                    description="读取文件 - 读取指定路径的文件内容",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "encoding": {"type": "string", "description": "文件编码", "default": "utf-8"}
                        },
                        "required": ["path"]
                    }
                ),
                types.Tool(
                    name="write_file",
                    description="写入文件 - 将内容写入指定路径的文件",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "content": {"type": "string", "description": "文件内容"},
                            "encoding": {"type": "string", "description": "文件编码", "default": "utf-8"}
                        },
                        "required": ["path", "content"]
                    }
                ),
                types.Tool(
                    name="list_files",
                    description="列出文件 - 列出指定目录下的文件和子目录",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "目录路径", "default": "."},
                            "recursive": {"type": "boolean", "description": "是否递归列出", "default": False},
                            "pattern": {"type": "string", "description": "文件名模式", "default": "*"}
                        }
                    }
                ),
                types.Tool(
                    name="read_many_files",
                    description="批量读取文件 - 一次读取多个文件的内容",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "paths": {"type": "array", "items": {"type": "string"}, "description": "文件路径数组"},
                            "encoding": {"type": "string", "description": "文件编码", "default": "utf-8"}
                        },
                        "required": ["paths"]
                    }
                ),
                types.Tool(
                    name="execute_command",
                    description="执行命令 - 在系统中执行命令行指令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "要执行的命令"},
                            "cwd": {"type": "string", "description": "工作目录", "default": "."},
                            "timeout": {"type": "integer", "description": "超时时间(秒)", "default": 30}
                        },
                        "required": ["command"]
                    }
                ),
                types.Tool(
                    name="grep",
                    description="Grep 搜索 - 在文件中搜索指定模式的文本",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "搜索模式"},
                            "path": {"type": "string", "description": "搜索路径", "default": "."},
                            "recursive": {"type": "boolean", "description": "是否递归搜索", "default": True}
                        },
                        "required": ["pattern"]
                    }
                ),
                types.Tool(
                    name="glob",
                    description="Glob 模式匹配 - 使用通配符模式查找文件",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "description": "Glob 模式"},
                            "path": {"type": "string", "description": "搜索路径", "default": "."},
                            "recursive": {"type": "boolean", "description": "是否递归搜索", "default": True}
                        },
                        "required": ["pattern"]
                    }
                ),
                types.Tool(
                    name="edit",
                    description="文件编辑 - 编辑文件内容，支持查找替换等操作",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                            "operation": {"type": "string", "description": "编辑操作类型"},
                            "content": {"type": "string", "description": "编辑内容"}
                        },
                        "required": ["path", "operation"]
                    }
                ),
                types.Tool(
                    name="web_fetch",
                    description="网络获取 - 从指定 URL 获取网页内容",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "目标 URL"},
                            "method": {"type": "string", "description": "HTTP 方法", "default": "GET"},
                            "timeout": {"type": "integer", "description": "超时时间(秒)", "default": 30}
                        },
                        "required": ["url"]
                    }
                ),
                types.Tool(
                    name="web_search",
                    description="网络搜索 - 在网络上搜索指定关键词",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "搜索查询"},
                            "max_results": {"type": "integer", "description": "最大结果数", "default": 10}
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="memory",
                    description="内存操作 - 存储、检索和管理内存中的数据",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "操作类型",
                                "enum": ["store", "retrieve", "delete", "list"]
                            },
                            "key": {"type": "string", "description": "数据键"},
                            "value": {"type": "string", "description": "数据值"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "标签列表"}
                        },
                        "required": ["operation"]
                    }
                )
            ]
        
        # 统一工具调用处理器
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
            """统一处理所有工具调用"""
            print(f"[DEBUG] 正在执行工具: {name}, 接收到的参数: {arguments}", file=sys.stderr)
            
            try:
                # 根据工具名称分发到对应的处理函数
                if name == "chat_completion":
                    return await self._handle_chat_completion(arguments)
                elif name == "analyze_code":
                    return await self._handle_analyze_code(arguments)
                elif name == "read_file":
                    return await self._handle_read_file(arguments)
                elif name == "write_file":
                    return await self._handle_write_file(arguments)
                elif name == "list_files":
                    return await self._handle_list_files(arguments)
                elif name == "read_many_files":
                    return await self._handle_read_many_files(arguments)
                elif name == "execute_command":
                    return await self._handle_execute_command(arguments)
                elif name == "grep":
                    return await self._handle_grep(arguments)
                elif name == "glob":
                    return await self._handle_glob(arguments)
                elif name == "edit":
                    return await self._handle_edit(arguments)
                elif name == "web_fetch":
                    return await self._handle_web_fetch(arguments)
                elif name == "web_search":
                    return await self._handle_web_search(arguments)
                elif name == "memory":
                    return await self._handle_memory(arguments)
                else:
                    error_msg = f"未知工具: {name}"
                    print(f"[ERROR] {error_msg}", file=sys.stderr)
                    return [types.TextContent(type="text", text=json.dumps({"error": error_msg}, ensure_ascii=False))]
            except Exception as e:
                error_msg = f"工具执行失败 ({name}): {str(e)}"
                print(f"[ERROR] {error_msg}", file=sys.stderr)
                return [types.TextContent(type="text", text=json.dumps({"error": error_msg}, ensure_ascii=False))]
    
    # 各个工具的具体实现函数
    async def _handle_chat_completion(self, arguments: dict) -> List[types.TextContent]:
        """处理聊天完成工具调用"""
        # 处理消息格式转换
        if 'messages' in arguments:
            messages = arguments['messages']
            converted_messages = []
            
            for msg in messages:
                if isinstance(msg, str):
                    # 如果是字符串，转换为用户消息
                    converted_messages.append({
                        "role": "user",
                        "content": msg
                    })
                elif isinstance(msg, dict):
                    # 如果是字典，直接使用
                    converted_messages.append(msg)
                else:
                    # 其他类型，尝试转换为字符串
                    converted_messages.append({
                        "role": "user",
                        "content": str(msg)
                    })
            
            arguments['messages'] = converted_messages
        
        args = ChatCompletionArgs(**arguments)
        result = await self.ai_client.chat_completion(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_analyze_code(self, arguments: dict) -> List[types.TextContent]:
        """处理代码分析工具调用"""
        args = CodeAnalysisArgs(**arguments)
        result = await self.ai_client.analyze_code(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_read_file(self, arguments: dict) -> List[types.TextContent]:
        """处理文件读取工具调用"""
        args = ReadFileArgs(**arguments)
        result = await self.file_ops.read_file(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_write_file(self, arguments: dict) -> List[types.TextContent]:
        """处理文件写入工具调用"""
        args = WriteFileArgs(**arguments)
        result = await self.file_ops.write_file(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_list_files(self, arguments: dict) -> List[types.TextContent]:
        """处理文件列表工具调用"""
        args = ListFilesArgs(**arguments)
        result = await self.file_ops.list_files(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_read_many_files(self, arguments: dict) -> List[types.TextContent]:
        """处理批量读取文件工具调用"""
        args = ReadManyFilesArgs(**arguments)
        result = await self.file_ops.read_many_files(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_execute_command(self, arguments: dict) -> List[types.TextContent]:
        """处理命令执行工具调用"""
        args = ExecuteCommandArgs(**arguments)
        result = await self.command_executor.execute_command(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_grep(self, arguments: dict) -> List[types.TextContent]:
        """处理Grep搜索工具调用"""
        args = GrepArgs(**arguments)
        result = await self.extended_tools.grep(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_glob(self, arguments: dict) -> List[types.TextContent]:
        """处理Glob模式匹配工具调用"""
        args = GlobArgs(**arguments)
        result = await self.extended_tools.glob(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_edit(self, arguments: dict) -> List[types.TextContent]:
        """处理文件编辑工具调用"""
        args = EditArgs(**arguments)
        result = await self.extended_tools.edit(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_web_fetch(self, arguments: dict) -> List[types.TextContent]:
        """处理网络获取工具调用"""
        args = WebFetchArgs(**arguments)
        result = await self.extended_tools.web_fetch(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_web_search(self, arguments: dict) -> List[types.TextContent]:
        """处理网络搜索工具调用"""
        args = WebSearchArgs(**arguments)
        result = await self.extended_tools.web_search(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    async def _handle_memory(self, arguments: dict) -> List[types.TextContent]:
        """处理内存操作工具调用"""
        # 检查是否传入了错误的参数格式
        if 'messages' in arguments and 'operation' not in arguments:
            error_msg = "错误：memory工具接收到了聊天消息参数，这可能是调用方式错误。正确的参数应该包含 'operation' 字段。"
            print(f"[SERVER] {error_msg}", file=sys.stderr)
            return [types.TextContent(type="text", text=json.dumps({"error": error_msg}, ensure_ascii=False))]
        
        args = MemoryArgs(**arguments)
        result = await self.extended_tools.memory_operation(args)
        return [types.TextContent(type="text", text=json.dumps(result.dict(), ensure_ascii=False))]
    
    def _register_resources(self):
        """注册资源"""
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[types.Resource]:
            """列出可用资源"""
            return [
                types.Resource(
                    uri=AnyUrl("config://server"),
                    name="服务器配置",
                    description="当前服务器配置信息",
                    mimeType="application/json"
                ),
                types.Resource(
                    uri=AnyUrl("temp://directory"),
                    name="临时目录",
                    description="临时文件目录信息",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri) -> str:
            """读取资源"""
            if uri == "config://server":
                return json.dumps(self.config.dict(), ensure_ascii=False, indent=2)
            elif uri == "temp://directory":
                temp_info = {
                    "path": self.config.temp_dir,
                    "exists": True,
                    "description": "临时文件存储目录"
                }
                return json.dumps(temp_info, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"未知资源: {uri}")
    
    async def run(self):
        """运行服务器"""
        print("[SERVER] 启动 Gemini Bridge MCP 服务器", file=sys.stderr)
        
        # 验证配置
        if not validate_config():
            print("[SERVER] 配置验证失败，服务器启动中止", file=sys.stderr)
            return
        
        # 打印配置信息
        print_config_info()
        
        # 运行服务器
        from mcp.server.stdio import stdio_server
        
        # 使用 stdio_server 运行 - 正确的 Python MCP 方式
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream, write_stream, self.server.create_initialization_options()
            )


async def main():
    """主函数"""
    try:
        server = GeminiBridgeServer()
        await server.run()
    except KeyboardInterrupt:
        print("\n[SERVER] 服务器已停止", file=sys.stderr)
    except Exception as e:
        print(f"[SERVER] 服务器运行错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
