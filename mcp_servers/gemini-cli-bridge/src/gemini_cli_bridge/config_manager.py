"""
配置管理器
负责加载和管理桥接服务器的配置
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from .types import BridgeConfig, LogLevel


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为 .env
        """
        self.config_file = config_file or ".env"
        self.config: Optional[BridgeConfig] = None
        self.logger = logging.getLogger(__name__)
        
        # 加载配置
        self._load_config()
        
    def _load_config(self) -> None:
        """加载配置"""
        try:
            # 加载环境变量
            if os.path.exists(self.config_file):
                load_dotenv(self.config_file)
                self.logger.info(f"已加载配置文件: {self.config_file}")
            else:
                self.logger.warning(f"配置文件不存在: {self.config_file}")
            
            # 从环境变量创建配置
            self.config = self._create_config_from_env()
            
            # 设置日志级别
            self._setup_logging()
            
            self.logger.info("配置加载完成")
            
        except Exception as e:
            self.logger.error(f"配置加载失败: {e}")
            raise
    
    def _create_config_from_env(self) -> BridgeConfig:
        """从环境变量创建配置"""
        # 必需的配置
        required_vars = [
            "CUSTOM_AI_API_URL",
            "CUSTOM_AI_MODEL", 
            "CUSTOM_AI_API_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"缺少必需的环境变量: {', '.join(missing_vars)}")
        
        # 创建配置对象
        config_data = {
            # 自定义 AI API 配置
            "custom_ai_api_url": os.getenv("CUSTOM_AI_API_URL"),
            "custom_ai_model": os.getenv("CUSTOM_AI_MODEL"),
            "custom_ai_api_key": os.getenv("CUSTOM_AI_API_KEY"),
            
            # Gemini CLI 配置
            "gemini_cli_path": os.getenv("GEMINI_CLI_PATH", "gemini"),
            "gemini_cli_workspace": os.getenv("GEMINI_CLI_WORKSPACE", "./workspace"),
            "gemini_cli_config_dir": os.getenv("GEMINI_CLI_CONFIG_DIR", "./config"),
            "gemini_cli_args": os.getenv("GEMINI_CLI_ARGS", ""),
            
            # API 代理配置
            "api_proxy_port": int(os.getenv("API_PROXY_PORT", "8888")),
            "api_proxy_host": os.getenv("API_PROXY_HOST", "localhost"),
            
            # 通用配置
            "bridge_log_level": LogLevel(os.getenv("BRIDGE_LOG_LEVEL", "INFO")),
            "bridge_timeout": int(os.getenv("BRIDGE_TIMEOUT", "60")),
            "bridge_max_retries": int(os.getenv("BRIDGE_MAX_RETRIES", "3")),
            
            # 高级配置
            "custom_settings_json": os.getenv("CUSTOM_SETTINGS_JSON"),
        }
        
        return BridgeConfig(**config_data)
    
    def _setup_logging(self) -> None:
        """设置日志"""
        if not self.config:
            return
            
        # 设置根日志记录器
        logging.basicConfig(
            level=getattr(logging, self.config.bridge_log_level.value),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def get_config(self) -> BridgeConfig:
        """获取配置"""
        if not self.config:
            raise RuntimeError("配置未加载")
        return self.config
    
    def create_gemini_settings(self) -> Dict[str, Any]:
        """创建 Gemini CLI 的 settings.json 配置"""
        if not self.config:
            raise RuntimeError("配置未加载")
        
        # 基础设置
        settings = {
            "apiKey": self.config.custom_ai_api_key,
            "model": self.config.custom_ai_model,
            "baseUrl": self.config.custom_ai_api_url,
            "timeout": self.config.bridge_timeout * 1000,  # 转换为毫秒
            "maxRetries": self.config.bridge_max_retries,
            "outputFormat": "json",
            "interactive": False,
            "browser": False,
        }
        
        return settings
    
    def ensure_directories(self) -> None:
        """确保必要的目录存在"""
        if not self.config:
            return
            
        directories = [
            self.config.gemini_cli_workspace,
            self.config.gemini_cli_config_dir,
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"确保目录存在: {directory}")
    
    def save_gemini_settings(self) -> str:
        """保存 Gemini CLI 设置文件"""
        if not self.config:
            raise RuntimeError("配置未加载")
        
        # 确保配置目录存在
        self.ensure_directories()
        
        # 创建设置
        settings = self.create_gemini_settings()
        
        # 确定设置文件路径
        if self.config.custom_settings_json:
            settings_path = self.config.custom_settings_json
        else:
            settings_path = os.path.join(self.config.gemini_cli_config_dir, "settings.json")
        
        # 保存设置文件
        settings_dir = os.path.dirname(settings_path)
        if settings_dir:
            Path(settings_dir).mkdir(parents=True, exist_ok=True)
        
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"已保存 Gemini CLI 设置: {settings_path}")
        return settings_path
    
    def get_gemini_env_vars(self) -> Dict[str, str]:
        """获取 Gemini CLI 需要的环境变量"""
        if not self.config:
            raise RuntimeError("配置未加载")
        
        env_vars = {
            "GEMINI_API_KEY": self.config.custom_ai_api_key,
            "GEMINI_MODEL": self.config.custom_ai_model,
            "GEMINI_BASE_URL": self.config.custom_ai_api_url,
        }
        
        return env_vars
    
    def reload_config(self) -> None:
        """重新加载配置"""
        self.logger.info("重新加载配置...")
        self._load_config()
    
    def validate_config(self) -> bool:
        """验证配置"""
        if not self.config:
            return False
        
        try:
            # 检查 Gemini CLI 是否可用
            import subprocess
            result = subprocess.run(
                [self.config.gemini_cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self.logger.error(f"Gemini CLI 不可用: {result.stderr}")
                return False
            
            self.logger.info(f"Gemini CLI 版本: {result.stdout.strip()}")
            return True
            
        except Exception as e:
            self.logger.error(f"验证 Gemini CLI 失败: {e}")
            return False
    
    def print_config_info(self) -> None:
        """打印配置信息"""
        if not self.config:
            print("配置未加载")
            return
        
        print("=== Gemini CLI Bridge 配置信息 ===")
        print(f"自定义 API URL: {self.config.custom_ai_api_url}")
        print(f"自定义模型: {self.config.custom_ai_model}")
        print(f"API 密钥: {'*' * (len(self.config.custom_ai_api_key) - 8) + self.config.custom_ai_api_key[-8:]}")
        print(f"Gemini CLI 路径: {self.config.gemini_cli_path}")
        print(f"工作目录: {self.config.gemini_cli_workspace}")
        print(f"配置目录: {self.config.gemini_cli_config_dir}")
        print(f"API 代理: {self.config.api_proxy_host}:{self.config.api_proxy_port}")
        print(f"日志级别: {self.config.bridge_log_level}")
        print(f"超时时间: {self.config.bridge_timeout}秒")
        print("================================")