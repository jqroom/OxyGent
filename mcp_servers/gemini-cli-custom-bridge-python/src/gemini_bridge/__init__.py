"""
Gemini CLI Custom Bridge Python 版本
一个 MCP 服务器，用于将 Gemini CLI 请求代理到自定义 AI 接口
"""

from .server import GeminiBridgeServer
from .config import get_server_config
from .path_manager import path_manager

__version__ = "1.0.0"
__all__ = ["GeminiBridgeServer", "get_server_config", "path_manager"]