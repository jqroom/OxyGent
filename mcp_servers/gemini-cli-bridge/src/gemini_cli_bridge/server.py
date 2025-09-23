"""
MCP 服务器主体
基于 Gemini CLI 的 MCP 桥接服务器
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import (
    Resource, 
    Tool, 
    TextContent, 
    ImageContent, 
    EmbeddedResource,
    ReadResourceResult,
    TextResourceContents
)
import mcp.types as types

from .types import (
    BridgeConfig, 
    ToolResult,
    GeminiChatArgs,
    GeminiAnalyzeArgs,
    GeminiFileOpsArgs,
    GeminiCommandArgs,
    GeminiToolsArgs,
    GeminiCustomArgs
)
from .config_manager import ConfigManager
from .gemini_wrapper import GeminiWrapper


class GeminiCliMcpServer:
    """Gemini CLI MCP 服务器"""
    
    def __init__(self):
        """初始化 MCP 服务器"""
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self.config_manager = ConfigManager()
        self.config = self.config_manager.get_config()
        
        # 创建 Gemini 包装器
        self.gemini_wrapper = GeminiWrapper(self.config)
        
        # 创建 MCP 服务器
        self.server = Server("gemini-cli-bridge")
        
        # 注册处理器
        self._register_handlers()
    
    def _register_handlers(self) -> None:
        """注册 MCP 处理器"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """列出可用工具"""
            return [
                Tool(
                    name="gemini_chat",
                    description="使用 Gemini CLI 进行聊天对话",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "聊天消息"
                            },
                            "files": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "相关文件列表（可选）"
                            },
                            "context": {
                                "type": "string",
                                "description": "上下文信息（可选）"
                            }
                        },
                        "required": ["message"]
                    }
                ),
                
                Tool(
                    name="gemini_analyze",
                    description="使用 Gemini CLI 分析代码或文件",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target": {
                                "type": "string",
                                "description": "分析目标（文件路径或代码内容）"
                            },
                            "analysis_type": {
                                "type": "string",
                                "description": "分析类型",
                                "enum": ["comprehensive", "security", "performance", "style", "bugs"],
                                "default": "comprehensive"
                            },
                            "focus": {
                                "type": "string",
                                "description": "分析重点（可选）"
                            }
                        },
                        "required": ["target"]
                    }
                ),
                
                Tool(
                    name="gemini_file_ops",
                    description="使用 Gemini CLI 进行文件操作",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "操作类型",
                                "enum": ["read", "write", "list", "search", "analyze"]
                            },
                            "path": {
                                "type": "string",
                                "description": "文件路径"
                            },
                            "content": {
                                "type": "string",
                                "description": "文件内容（写入时使用）"
                            },
                            "pattern": {
                                "type": "string",
                                "description": "搜索模式（搜索时使用）"
                            }
                        },
                        "required": ["operation", "path"]
                    }
                ),
                
                Tool(
                    name="gemini_command",
                    description="使用 Gemini CLI 执行系统命令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "要执行的命令"
                            },
                            "working_dir": {
                                "type": "string",
                                "description": "工作目录（可选）"
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "超时时间（秒）",
                                "default": 30
                            }
                        },
                        "required": ["command"]
                    }
                ),
                
                Tool(
                    name="gemini_tools",
                    description="使用 Gemini CLI 的内置工具",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tool_name": {
                                "type": "string",
                                "description": "工具名称"
                            },
                            "tool_args": {
                                "type": "object",
                                "description": "工具参数",
                                "additionalProperties": True
                            }
                        },
                        "required": ["tool_name"]
                    }
                ),
                
                Tool(
                    name="gemini_custom",
                    description="执行自定义 Gemini CLI 操作",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "operation": {
                                "type": "string",
                                "description": "自定义操作名称"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "操作参数",
                                "additionalProperties": True
                            }
                        },
                        "required": ["operation"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> Sequence[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """处理工具调用"""
            try:
                self.logger.info(f"调用工具: {name}, 参数: {arguments}")
                
                result: ToolResult
                
                if name == "gemini_chat":
                    args = GeminiChatArgs(**arguments)
                    result = await self.gemini_wrapper.chat(
                        message=args.message,
                        files=args.files,
                        context=args.context
                    )
                
                elif name == "gemini_analyze":
                    args = GeminiAnalyzeArgs(**arguments)
                    result = await self.gemini_wrapper.analyze_code(
                        target=args.target,
                        analysis_type=args.analysis_type,
                        focus=args.focus
                    )
                
                elif name == "gemini_file_ops":
                    args = GeminiFileOpsArgs(**arguments)
                    result = await self.gemini_wrapper.file_operations(
                        operation=args.operation,
                        path=args.path,
                        content=args.content,
                        pattern=args.pattern
                    )
                
                elif name == "gemini_command":
                    args = GeminiCommandArgs(**arguments)
                    result = await self.gemini_wrapper.execute_system_command(
                        command=args.command,
                        working_dir=args.working_dir,
                        timeout=args.timeout
                    )
                
                elif name == "gemini_tools":
                    args = GeminiToolsArgs(**arguments)
                    result = await self.gemini_wrapper.use_tools(
                        tool_name=args.tool_name,
                        tool_args=args.tool_args
                    )
                
                elif name == "gemini_custom":
                    args = GeminiCustomArgs(**arguments)
                    result = await self.gemini_wrapper.custom_operation(
                        operation=args.operation,
                        parameters=args.parameters
                    )
                
                else:
                    raise ValueError(f"未知工具: {name}")
                
                # 构建响应
                response_content = []
                
                if result.success:
                    response_content.append(
                        TextContent(
                            type="text",
                            text=result.content
                        )
                    )
                    
                    # 如果有元数据，添加到响应中
                    if result.metadata:
                        metadata_text = f"\n\n**元数据:**\n```json\n{result.metadata}\n```"
                        response_content.append(
                            TextContent(
                                type="text",
                                text=metadata_text
                            )
                        )
                else:
                    error_text = f"❌ 工具执行失败: {result.error}"
                    response_content.append(
                        TextContent(
                            type="text",
                            text=error_text
                        )
                    )
                
                self.logger.info(f"工具执行完成: {name}, 成功: {result.success}")
                return response_content
                
            except Exception as e:
                self.logger.error(f"工具调用失败: {name}, 错误: {e}")
                return [
                    TextContent(
                        type="text",
                        text=f"❌ 工具调用失败: {str(e)}"
                    )
                ]
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:
            """列出可用资源"""
            return [
                Resource(
                    uri="gemini://status",
                    name="Gemini CLI Bridge 状态",
                    description="获取桥接服务器的状态信息",
                    mimeType="application/json"
                ),
                Resource(
                    uri="gemini://config",
                    name="Gemini CLI Bridge 配置",
                    description="获取桥接服务器的配置信息",
                    mimeType="application/json"
                ),
                Resource(
                    uri="gemini://health",
                    name="Gemini CLI 健康检查",
                    description="检查 Gemini CLI 的健康状态",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> ReadResourceResult:
            """读取资源"""
            try:
                self.logger.info(f"读取资源: {uri}")
                
                if uri == "gemini://status":
                    status = self.gemini_wrapper.get_status()
                    return ReadResourceResult(
                        contents=[TextResourceContents(uri="gemini://status", text=f"```json\n{status}\n```")]
                    )
                
                elif uri == "gemini://config":
                    # 返回配置信息（隐藏敏感信息）
                    config_info = {
                        "custom_ai_api_url": self.config.custom_ai_api_url,
                        "custom_ai_model": self.config.custom_ai_model,
                        "gemini_cli_path": self.config.gemini_cli_path,
                        "gemini_cli_workspace": self.config.gemini_cli_workspace,
                        "api_proxy_host": self.config.api_proxy_host,
                        "api_proxy_port": self.config.api_proxy_port,
                        "bridge_log_level": self.config.bridge_log_level,
                        "bridge_timeout": self.config.bridge_timeout,
                    }
                    return ReadResourceResult(
                        contents=[TextResourceContents(uri="gemini://config", text=f"```json\n{config_info}\n```")]
                    )
                
                elif uri == "gemini://health":
                    health = await self.gemini_wrapper.health_check()
                    health_info = {
                        "healthy": health,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    return ReadResourceResult(
                        contents=[TextResourceContents(uri="gemini://health", text=f"```json\n{health_info}\n```")]
                    )
                
                else:
                    raise ValueError(f"未知资源: {uri}")
                    
            except Exception as e:
                self.logger.error(f"读取资源失败: {uri}, 错误: {e}")
                return ReadResourceResult(
                    contents=[TextResourceContents(uri=uri, text=f"❌ 读取资源失败: {str(e)}")]
                )
    
    async def start(self) -> None:
        """启动服务器"""
        try:
            # 验证配置
            if not self.config_manager.validate_config():
                raise RuntimeError("配置验证失败")
            
            # 启动 API 代理
            await self.gemini_wrapper.start_proxy()
            
            self.logger.info("Gemini CLI MCP 桥接服务器已启动")
            
        except Exception as e:
            self.logger.error(f"启动服务器失败: {e}")
            raise
    
    async def stop(self) -> None:
        """停止服务器"""
        try:
            # 停止 API 代理
            await self.gemini_wrapper.stop_proxy()
            
            self.logger.info("Gemini CLI MCP 桥接服务器已停止")
            
        except Exception as e:
            self.logger.error(f"停止服务器失败: {e}")
    
    def get_server(self) -> Server:
        """获取 MCP 服务器实例"""
        return self.server


# 主函数
async def main():
    """主函数"""
    # 创建服务器
    mcp_server = GeminiCliMcpServer()
    
    try:
        # 启动服务器
        await mcp_server.start()
        
        # 运行 MCP 服务器
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.get_server().run(
                read_stream, 
                write_stream, 
                InitializationOptions(
                    server_name="gemini-cli-bridge",
                    server_version="1.0.0",
                    capabilities=mcp_server.get_server().get_capabilities(
                        NotificationOptions(),
                        {}
                    )
                )
            )
    
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在停止服务器...")
    
    except Exception as e:
        import traceback
        logging.error(f"服务器运行失败: {e}")
        logging.error(f"详细错误信息: {traceback.format_exc()}")
        raise
    
    finally:
        # 停止服务器
        await mcp_server.stop()


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行服务器
    asyncio.run(main())