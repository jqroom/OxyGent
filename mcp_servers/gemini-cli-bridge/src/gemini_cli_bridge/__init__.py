"""
Gemini CLI Bridge MCP Server

一个基于原版 Google Gemini CLI 的 MCP 桥接服务器，支持自定义 API 接口配置。
"""

__version__ = "1.0.0"
__author__ = "AutoDev Team"
__description__ = "MCP Bridge Server for Google Gemini CLI with Custom API Support"

from .server import GeminiCliMcpServer
from .config_manager import ConfigManager
from .gemini_wrapper import GeminiWrapper
from .api_proxy import ApiProxy

__all__ = [
    "GeminiCliBridgeServer",
    "ConfigManager", 
    "GeminiWrapper",
    "ApiProxy",
]