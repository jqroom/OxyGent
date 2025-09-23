"""
类型定义和数据模型
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class LogLevel(str, Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class BridgeConfig(BaseModel):
    """桥接服务器配置"""
    # 自定义 AI API 配置
    custom_ai_api_url: str = Field(..., description="自定义 AI API URL")
    custom_ai_model: str = Field(..., description="自定义 AI 模型名称")
    custom_ai_api_key: str = Field(..., description="自定义 AI API 密钥")
    
    # Gemini CLI 配置
    gemini_cli_path: str = Field(default="gemini", description="Gemini CLI 命令路径")
    gemini_cli_workspace: str = Field(default="./workspace", description="Gemini CLI 工作目录")
    gemini_cli_config_dir: str = Field(default="./config", description="Gemini CLI 配置目录")
    gemini_cli_args: str = Field(default="", description="Gemini CLI 额外参数")
    
    # API 代理配置
    api_proxy_port: int = Field(default=8888, description="API 代理端口")
    api_proxy_host: str = Field(default="localhost", description="API 代理主机")
    
    # 通用配置
    bridge_log_level: LogLevel = Field(default=LogLevel.INFO, description="日志级别")
    bridge_timeout: int = Field(default=60, description="超时时间(秒)")
    bridge_max_retries: int = Field(default=3, description="最大重试次数")
    
    # 高级配置
    custom_settings_json: Optional[str] = Field(default=None, description="自定义 settings.json 路径")


class GeminiRequest(BaseModel):
    """Gemini CLI 请求"""
    command: str = Field(..., description="命令类型")
    prompt: Optional[str] = Field(default=None, description="用户提示")
    files: Optional[List[str]] = Field(default=None, description="文件列表")
    args: Optional[Dict[str, Any]] = Field(default=None, description="额外参数")
    working_dir: Optional[str] = Field(default=None, description="工作目录")


class GeminiResponse(BaseModel):
    """Gemini CLI 响应"""
    success: bool = Field(..., description="是否成功")
    output: str = Field(default="", description="输出内容")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class ApiProxyRequest(BaseModel):
    """API 代理请求"""
    method: str = Field(..., description="HTTP 方法")
    url: str = Field(..., description="请求 URL")
    headers: Optional[Dict[str, str]] = Field(default=None, description="请求头")
    data: Optional[Union[str, Dict[str, Any]]] = Field(default=None, description="请求数据")


class ApiProxyResponse(BaseModel):
    """API 代理响应"""
    status_code: int = Field(..., description="HTTP 状态码")
    headers: Dict[str, str] = Field(default_factory=dict, description="响应头")
    content: str = Field(default="", description="响应内容")


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = Field(..., description="是否成功")
    content: str = Field(default="", description="结果内容")
    error: Optional[str] = Field(default=None, description="错误信息")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


# MCP 工具参数类型定义
class GeminiChatArgs(BaseModel):
    """Gemini 聊天参数"""
    message: str = Field(..., description="聊天消息")
    files: Optional[List[str]] = Field(default=None, description="相关文件")
    context: Optional[str] = Field(default=None, description="上下文")


class GeminiAnalyzeArgs(BaseModel):
    """Gemini 分析参数"""
    target: str = Field(..., description="分析目标（文件或代码）")
    analysis_type: str = Field(default="comprehensive", description="分析类型")
    focus: Optional[str] = Field(default=None, description="分析重点")


class GeminiFileOpsArgs(BaseModel):
    """Gemini 文件操作参数"""
    operation: str = Field(..., description="操作类型 (read/write/list/search)")
    path: str = Field(..., description="文件路径")
    content: Optional[str] = Field(default=None, description="文件内容（写入时）")
    pattern: Optional[str] = Field(default=None, description="搜索模式")


class GeminiCommandArgs(BaseModel):
    """Gemini 命令执行参数"""
    command: str = Field(..., description="要执行的命令")
    working_dir: Optional[str] = Field(default=None, description="工作目录")
    timeout: Optional[int] = Field(default=30, description="超时时间")


class GeminiToolsArgs(BaseModel):
    """Gemini 工具使用参数"""
    tool_name: str = Field(..., description="工具名称")
    tool_args: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class GeminiCustomArgs(BaseModel):
    """Gemini 自定义操作参数"""
    operation: str = Field(..., description="自定义操作")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")