"""
配置管理模块
负责加载和管理环境变量、配置文件等
"""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .types import ServerConfig, AIConfig


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self._config: Optional[ServerConfig] = None
        self._ai_config: Optional[AIConfig] = None
        self._load_environment()
    
    def _load_environment(self):
        """加载环境变量"""
        # 查找 .env 文件
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        
        # 按优先级查找 .env 文件
        env_paths = [
            current_dir / ".env",  # 模块目录
            project_root / ".env",  # 项目根目录
            Path.cwd() / ".env",   # 当前工作目录
        ]
        
        for env_path in env_paths:
            if env_path.exists():
                print(f"[CONFIG] 加载环境变量文件: {env_path}", file=sys.stderr)
                load_dotenv(env_path)
                break
        else:
            print("[CONFIG] 未找到 .env 文件，使用系统环境变量", file=sys.stderr)
    
    def get_server_config(self) -> ServerConfig:
        """获取服务器配置"""
        if self._config is None:
            self._config = self._create_server_config()
        return self._config
    
    def get_ai_config(self) -> AIConfig:
        """获取 AI 配置"""
        if self._ai_config is None:
            self._ai_config = self._create_ai_config()
        return self._ai_config
    
    def _create_server_config(self) -> ServerConfig:
        """创建服务器配置"""
        # 获取项目根目录和沙盒目录
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent
        sandbox_dir = project_root / "cache_dir" / "gemini_cli_workspace"
        
        # 确保沙盒目录存在
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        
        return ServerConfig(
            name="gemini-cli-custom-bridge-python",
            version="1.0.0",
            description="Python version of Gemini CLI Custom Bridge MCP Server - Sandbox Mode",
            ai_api_url=self._get_required_env("NEXT_PUBLIC_AI_API_URL"),
            ai_model=self._get_env("NEXT_PUBLIC_AI_MODEL", "gpt-3.5-turbo"),
            ai_api_key=self._get_required_env("NEXT_PUBLIC_AI_API_KEY"),
            temp_dir=str(sandbox_dir),
            project_root=str(project_root),
            timeout=int(self._get_env("AI_TIMEOUT", "30")),
            max_file_size=int(self._get_env("MAX_FILE_SIZE", str(10 * 1024 * 1024)))
        )
    
    def _create_ai_config(self) -> AIConfig:
        """创建 AI 配置"""
        return AIConfig(
            api_url=self._get_required_env("NEXT_PUBLIC_AI_API_URL"),
            model=self._get_env("NEXT_PUBLIC_AI_MODEL", "gpt-3.5-turbo"),
            api_key=self._get_required_env("NEXT_PUBLIC_AI_API_KEY"),
            temperature=float(self._get_env("AI_TEMPERATURE", "0.7")),
            max_tokens=int(self._get_env("AI_MAX_TOKENS", "2000"))
        )
    
    def _get_env(self, key: str, default: str = "") -> str:
        """获取环境变量"""
        value = os.getenv(key, default)
        if not value and not default:
            print(f"[CONFIG] 警告: 环境变量 {key} 未设置", file=sys.stderr)
        return value
    
    def _get_required_env(self, key: str) -> str:
        """获取必需的环境变量"""
        value = os.getenv(key)
        if not value:
            error_msg = f"必需的环境变量 {key} 未设置"
            print(f"[CONFIG] 错误: {error_msg}", file=sys.stderr)
            raise ValueError(error_msg)
        return value
    
    def validate_config(self) -> bool:
        """验证配置是否有效"""
        try:
            config = self.get_server_config()
            ai_config = self.get_ai_config()
            
            # 验证必需字段
            if not config.ai_api_url:
                print("[CONFIG] 错误: AI API URL 未配置", file=sys.stderr)
                return False
            
            if not config.ai_api_key:
                print("[CONFIG] 错误: AI API Key 未配置", file=sys.stderr)
                return False
            
            if not config.ai_model:
                print("[CONFIG] 错误: AI Model 未配置", file=sys.stderr)
                return False
            
            # 验证目录路径
            sandbox_path = Path(config.temp_dir)
            if not sandbox_path.exists():
                print(f"[CONFIG] 创建沙盒目录: {sandbox_path}", file=sys.stderr)
                sandbox_path.mkdir(parents=True, exist_ok=True)
            
            print("[CONFIG] 配置验证通过", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"[CONFIG] 配置验证失败: {e}", file=sys.stderr)
            return False
    
    def print_config_info(self):
        """打印配置信息（隐藏敏感信息）"""
        try:
            config = self.get_server_config()
            
            print(f"[CONFIG] 服务器配置:", file=sys.stderr)
            print(f"[CONFIG]   - 名称: {config.name}", file=sys.stderr)
            print(f"[CONFIG]   - 版本: {config.version}", file=sys.stderr)
            print(f"[CONFIG]   - AI API URL: {config.ai_api_url}", file=sys.stderr)
            print(f"[CONFIG]   - AI Model: {config.ai_model}", file=sys.stderr)
            print(f"[CONFIG]   - AI API Key: {'*' * (len(config.ai_api_key) - 4) + config.ai_api_key[-4:] if len(config.ai_api_key) > 4 else '****'}", file=sys.stderr)
            print(f"[CONFIG]   - 沙盒目录: {config.temp_dir}", file=sys.stderr)
            print(f"[CONFIG]   - 项目根目录: {config.project_root}", file=sys.stderr)
            print(f"[CONFIG]   - 超时时间: {config.timeout}s", file=sys.stderr)
            print(f"[CONFIG]   - 最大文件大小: {config.max_file_size} bytes", file=sys.stderr)
            
        except Exception as e:
            print(f"[CONFIG] 无法打印配置信息: {e}", file=sys.stderr)


# 全局配置管理器实例
config_manager = ConfigManager()


def get_server_config() -> ServerConfig:
    """获取服务器配置"""
    return config_manager.get_server_config()


def get_ai_config() -> AIConfig:
    """获取 AI 配置"""
    return config_manager.get_ai_config()


def validate_config() -> bool:
    """验证配置"""
    return config_manager.validate_config()


def print_config_info():
    """打印配置信息"""
    config_manager.print_config_info()