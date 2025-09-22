#!/usr/bin/env python3
"""
Gemini CLI MCP 服务器实现

这个模块实现了一个完整的 MCP 服务器，将 Gemini CLI 功能暴露为 MCP 工具和资源。
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# MCP 相关导入
try:
    from mcp.server import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolResult,
        ListResourcesResult,
        ListToolsResult,
        Resource,
        TextContent,
        Tool,
        INVALID_PARAMS,
        INTERNAL_ERROR,
    )
    from pydantic import AnyUrl
except ImportError:
    print("错误：未安装 MCP SDK。请运行: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    from .gemini_cli_config import GeminiCLIConfig, get_config
except ImportError:
    # 当直接运行此文件时，使用绝对导入
    from gemini_cli_config import GeminiCLIConfig, get_config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiCLIMCPServer:
    """Gemini CLI MCP 服务器类。"""
    
    def __init__(self):
        self.server = Server("gemini-cli")
        self.config: Optional[GeminiCLIConfig] = None
        self._setup_handlers()
    
    def _setup_handlers(self):
        """设置 MCP 处理器。"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出可用的工具。"""
            return [
                Tool(
                    name="gemini_chat",
                    description="与 Gemini 模型进行聊天对话",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "聊天提示词"
                            },
                            "model": {
                                "type": "string",
                                "description": "模型名称",
                                "default": "gemini-2.0-flash-exp"
                            },
                            "temperature": {
                                "type": "number",
                                "description": "温度参数",
                                "minimum": 0.0,
                                "maximum": 2.0,
                                "default": 0.7
                            }
                        },
                        "required": ["prompt"]
                    }
                ),
                Tool(
                    name="gemini_analyze_code",
                    description="使用 Gemini 分析代码",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "code": {
                                "type": "string",
                                "description": "要分析的代码"
                            },
                            "analysis_type": {
                                "type": "string",
                                "description": "分析类型",
                                "enum": ["general", "security", "performance", "style", "documentation"],
                                "default": "general"
                            },
                            "language": {
                                "type": "string",
                                "description": "编程语言",
                                "default": "python"
                            }
                        },
                        "required": ["code"]
                    }
                ),
                Tool(
                    name="gemini_generate_code",
                    description="使用 Gemini 生成代码",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "代码功能描述"
                            },
                            "language": {
                                "type": "string",
                                "description": "目标编程语言",
                                "default": "python"
                            },
                            "style": {
                                "type": "string",
                                "description": "代码风格要求",
                                "default": "clean and readable"
                            }
                        },
                        "required": ["description"]
                    }
                ),
                Tool(
                    name="gemini_execute_command",
                    description="执行自定义 Gemini CLI 命令",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Gemini CLI 命令参数"
                            },
                            "input_text": {
                                "type": "string",
                                "description": "输入文本（可选）",
                                "default": ""
                            }
                        },
                        "required": ["command"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """调用工具。"""
            try:
                if name == "gemini_chat":
                    return await self._handle_chat(arguments)
                elif name == "gemini_analyze_code":
                    return await self._handle_analyze_code(arguments)
                elif name == "gemini_generate_code":
                    return await self._handle_generate_code(arguments)
                elif name == "gemini_execute_command":
                    return await self._handle_execute_command(arguments)
                else:
                    return [TextContent(type="text", text=f"未知工具: {name}")]
            except Exception as e:
                logger.error(f"工具调用失败: {e}")
                return [TextContent(type="text", text=f"工具调用失败: {str(e)}")]
        
        @self.server.list_resources()
        async def list_resources() -> List[Resource]:
            """列出可用的资源。"""
            return [
                Resource(
                    uri=AnyUrl("file://gemini/config"),
                    name="Gemini CLI 配置",
                    description="当前 Gemini CLI 配置信息",
                    mimeType="application/json"
                ),
                Resource(
                    uri=AnyUrl("file://gemini/status"),
                    name="Gemini CLI 状态",
                    description="Gemini CLI 安装和连接状态",
                    mimeType="application/json"
                )
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: AnyUrl) -> str:
            """读取资源。"""
            try:
                if uri == "file://gemini/config":
                    config = self._get_config()
                    config_data = {
                        "cli_path": config.cli_path,
                        "model_name": config.model_name,
                        "temperature": config.temperature,
                        "max_tokens": config.max_tokens,
                        "timeout": config.timeout,
                        "max_retries": config.max_retries,
                        "enable_cache": config.enable_cache,
                        "api_key_configured": bool(config.api_key)
                    }
                    return json.dumps(config_data, indent=2, ensure_ascii=False)
                elif uri == "file://gemini/status":
                    status = await self._check_status()
                    return json.dumps(status, indent=2, ensure_ascii=False)
                else:
                    return f"未知资源: {uri}"
            except Exception as e:
                logger.error(f"读取资源失败: {e}")
                return f"读取资源失败: {str(e)}"
    
    def _get_config(self) -> GeminiCLIConfig:
        """获取配置。"""
        if self.config is None:
            self.config = get_config()
        return self.config
    
    async def _check_status(self) -> Dict[str, Any]:
        """检查 Gemini CLI 状态。"""
        config = self._get_config()
        status = {
            "cli_installed": False,
            "cli_version": None,
            "api_key_configured": bool(config.api_key),
            "connection_test": False,
            "error": None
        }
        
        try:
            # 检查 CLI 安装
            result = subprocess.run(
                [config.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                status["cli_installed"] = True
                status["cli_version"] = result.stdout.strip()
                
                # 如果有 API 密钥，测试连接
                if config.api_key:
                    test_result = await self._test_connection(config)
                    status["connection_test"] = test_result["success"]
                    if not test_result["success"]:
                        status["error"] = test_result["error"]
            else:
                status["error"] = result.stderr
                
        except FileNotFoundError:
            status["error"] = f"找不到 Gemini CLI: {config.cli_path}"
        except subprocess.TimeoutExpired:
            status["error"] = "CLI 版本检查超时"
        except Exception as e:
            status["error"] = str(e)
        
        return status
    
    async def _test_connection(self, config: GeminiCLIConfig) -> Dict[str, Any]:
        """测试连接。"""
        try:
            env = {**os.environ, "GEMINI_API_KEY": config.api_key}
            if config.project_id:
                env["GOOGLE_CLOUD_PROJECT"] = config.project_id
            
            result = subprocess.run(
                [config.cli_path, "chat", "--prompt", "Hello", "--model", config.model_name],
                capture_output=True,
                text=True,
                timeout=config.timeout,
                env=env
            )
            
            return {
                "success": result.returncode == 0,
                "error": result.stderr if result.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_gemini_command(self, command: List[str], input_text: str = "") -> Dict[str, Any]:
        """执行 Gemini CLI 命令。"""
        config = self._get_config()
        
        if not config.api_key:
            return {
                "success": False,
                "error": "未配置 API 密钥，请设置 GEMINI_API_KEY 环境变量"
            }
        
        try:
            # 设置环境变量
            env = {**os.environ, "GEMINI_API_KEY": config.api_key}
            if config.project_id:
                env["GOOGLE_CLOUD_PROJECT"] = config.project_id
            
            # 构建完整命令
            full_command = [config.cli_path] + command
            
            # 执行命令
            result = subprocess.run(
                full_command,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=config.timeout,
                env=env
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "命令执行超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _handle_chat(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理聊天请求。"""
        prompt = arguments.get("prompt", "")
        model = arguments.get("model", "gemini-2.0-flash-exp")
        temperature = arguments.get("temperature", 0.7)
        
        command = [
            "chat",
            "--prompt", prompt,
            "--model", model,
            "--temperature", str(temperature)
        ]
        
        result = await self._execute_gemini_command(command)
        
        if result["success"]:
            return [TextContent(type="text", text=result["output"])]
        else:
            return [TextContent(type="text", text=f"聊天失败: {result['error']}")]
    
    async def _handle_analyze_code(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理代码分析请求。"""
        code = arguments.get("code", "")
        analysis_type = arguments.get("analysis_type", "general")
        language = arguments.get("language", "python")
        
        # 构建分析提示
        analysis_prompts = {
            "general": f"请分析以下 {language} 代码的整体质量、结构和可能的改进点：\n\n{code}",
            "security": f"请分析以下 {language} 代码的安全性，识别潜在的安全漏洞：\n\n{code}",
            "performance": f"请分析以下 {language} 代码的性能，提供优化建议：\n\n{code}",
            "style": f"请分析以下 {language} 代码的风格和可读性，提供改进建议：\n\n{code}",
            "documentation": f"请分析以下 {language} 代码的文档完整性，建议添加注释和文档：\n\n{code}"
        }
        
        prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])
        
        command = ["chat", "--prompt", prompt]
        result = await self._execute_gemini_command(command)
        
        if result["success"]:
            return [TextContent(type="text", text=result["output"])]
        else:
            return [TextContent(type="text", text=f"代码分析失败: {result['error']}")]
    
    async def _handle_generate_code(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理代码生成请求。"""
        description = arguments.get("description", "")
        language = arguments.get("language", "python")
        style = arguments.get("style", "clean and readable")
        
        prompt = f"请用 {language} 编写代码来实现以下功能：{description}\n\n要求：\n- 代码风格：{style}\n- 包含必要的注释\n- 遵循最佳实践"
        
        command = ["chat", "--prompt", prompt]
        result = await self._execute_gemini_command(command)
        
        if result["success"]:
            return [TextContent(type="text", text=result["output"])]
        else:
            return [TextContent(type="text", text=f"代码生成失败: {result['error']}")]
    
    async def _handle_execute_command(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """处理自定义命令执行请求。"""
        command = arguments.get("command", [])
        input_text = arguments.get("input_text", "")
        
        if not command:
            return [TextContent(type="text", text="命令不能为空")]
        
        result = await self._execute_gemini_command(command, input_text)
        
        if result["success"]:
            return [TextContent(type="text", text=result["output"])]
        else:
            return [TextContent(type="text", text=f"命令执行失败: {result['error']}")]


async def main():
    """主函数。"""
    server_instance = GeminiCLIMCPServer()
    
    # 创建通知选项
    notification_options = NotificationOptions(
        prompts_changed=False,
        resources_changed=False,
        tools_changed=False
    )
    
    # 运行服务器
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gemini-cli",
                server_version="1.0.0",
                capabilities=server_instance.server.get_capabilities(
                    notification_options=notification_options,
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())