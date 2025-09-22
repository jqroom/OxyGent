"""Gemini CLI 工具配置管理模块。

提供 Gemini CLI 集成所需的配置管理和身份验证功能。
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Any
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class GeminiCLIConfig(BaseModel):
    """Gemini CLI 配置类。"""
    
    # API 配置
    api_key: Optional[str] = Field(None, description="Gemini API 密钥")
    project_id: Optional[str] = Field(None, description="Google Cloud 项目 ID")
    region: str = Field("us-central1", description="服务区域")
    
    # CLI 配置
    cli_path: str = Field("gemini", description="Gemini CLI 可执行文件路径")
    timeout: int = Field(30, description="命令执行超时时间（秒）")
    max_retries: int = Field(3, description="最大重试次数")
    
    # 模型配置
    model_name: str = Field("gemini-2.0-flash-exp", description="默认使用的模型")
    temperature: float = Field(0.7, description="生成温度")
    max_tokens: int = Field(8192, description="最大输出 token 数")
    
    # 缓存配置
    enable_cache: bool = Field(True, description="是否启用响应缓存")
    cache_ttl: int = Field(3600, description="缓存生存时间（秒）")
    
    class Config:
        """Pydantic 配置。"""
        env_prefix = "GEMINI_"
        case_sensitive = False


class GeminiConfigManager:
    """Gemini CLI 配置管理器。"""
    
    def __init__(self, config_path: Optional[str] = None):
        """初始化配置管理器。
        
        Args:
            config_path: 配置文件路径，默认为 ~/.oxygent/gemini_config.json
        """
        if config_path is None:
            config_dir = Path.home() / ".oxygent"
            config_dir.mkdir(exist_ok=True)
            self.config_path = config_dir / "gemini_config.json"
        else:
            self.config_path = Path(config_path)
        
        self._config: Optional[GeminiCLIConfig] = None
        
    def load_config(self) -> GeminiCLIConfig:
        """加载配置。
        
        Returns:
            GeminiCLIConfig: 配置对象
        """
        if self._config is not None:
            return self._config
            
        config_data = {}
        
        # 从文件加载配置
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                logger.info(f"从 {self.config_path} 加载配置")
            except Exception as e:
                logger.warning(f"加载配置文件失败: {e}")
        
        # 从环境变量加载配置
        env_config = self._load_from_env()
        config_data.update(env_config)
        
        # 创建配置对象
        self._config = GeminiCLIConfig(**config_data)
        
        # 验证配置
        self._validate_config()
        
        return self._config
    
    def save_config(self, config: GeminiCLIConfig) -> None:
        """保存配置到文件。
        
        Args:
            config: 要保存的配置对象
        """
        try:
            # 确保目录存在
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存配置（排除敏感信息）
            config_dict = config.dict()
            if config_dict.get('api_key'):
                config_dict['api_key'] = '***masked***'
                
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                
            logger.info(f"配置已保存到 {self.config_path}")
            self._config = config
            
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            raise
    
    def _load_from_env(self) -> Dict[str, Any]:
        """从环境变量加载配置。
        
        Returns:
            Dict[str, Any]: 环境变量配置
        """
        env_config = {}
        
        # API 配置
        if api_key := os.getenv('GEMINI_API_KEY'):
            env_config['api_key'] = api_key
        if project_id := os.getenv('GEMINI_PROJECT_ID'):
            env_config['project_id'] = project_id
        if region := os.getenv('GEMINI_REGION'):
            env_config['region'] = region
            
        # CLI 配置
        if cli_path := os.getenv('GEMINI_CLI_PATH'):
            env_config['cli_path'] = cli_path
        if timeout := os.getenv('GEMINI_TIMEOUT'):
            try:
                env_config['timeout'] = int(timeout)
            except ValueError:
                logger.warning(f"无效的 GEMINI_TIMEOUT 值: {timeout}")
                
        # 模型配置
        if model_name := os.getenv('GEMINI_MODEL_NAME'):
            env_config['model_name'] = model_name
        if temperature := os.getenv('GEMINI_TEMPERATURE'):
            try:
                env_config['temperature'] = float(temperature)
            except ValueError:
                logger.warning(f"无效的 GEMINI_TEMPERATURE 值: {temperature}")
        
        return env_config
    
    def _validate_config(self) -> None:
        """验证配置有效性。"""
        if not self._config:
            return
            
        # 检查 CLI 可执行文件
        try:
            import subprocess
            result = subprocess.run(
                [self._config.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.warning(f"Gemini CLI 可能未正确安装: {self._config.cli_path}")
        except Exception as e:
            logger.warning(f"无法验证 Gemini CLI: {e}")
    
    def get_auth_env(self) -> Dict[str, str]:
        """获取身份验证环境变量。
        
        Returns:
            Dict[str, str]: 环境变量字典
        """
        config = self.load_config()
        env = {}
        
        if config.api_key:
            env['GEMINI_API_KEY'] = config.api_key
        if config.project_id:
            env['GOOGLE_CLOUD_PROJECT'] = config.project_id
            
        return env
    
    def update_config(self, **kwargs) -> None:
        """更新配置。
        
        Args:
            **kwargs: 要更新的配置项
        """
        config = self.load_config()
        
        # 更新配置
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                logger.warning(f"未知的配置项: {key}")
        
        # 保存更新后的配置
        self.save_config(config)


# 全局配置管理器实例
config_manager = GeminiConfigManager()


def get_config() -> GeminiCLIConfig:
    """获取全局配置。
    
    Returns:
        GeminiCLIConfig: 配置对象
    """
    return config_manager.load_config()


def setup_gemini_cli() -> bool:
    """设置 Gemini CLI 环境。
    
    Returns:
        bool: 设置是否成功
    """
    try:
        config = get_config()
        
        # 设置环境变量
        auth_env = config_manager.get_auth_env()
        for key, value in auth_env.items():
            os.environ[key] = value
            
        logger.info("Gemini CLI 环境设置完成")
        return True
        
    except Exception as e:
        logger.error(f"设置 Gemini CLI 环境失败: {e}")
        return False


def create_default_config() -> GeminiCLIConfig:
    """创建默认配置。
    
    Returns:
        GeminiCLIConfig: 默认配置对象
    """
    # 使用默认值创建配置
    config = GeminiCLIConfig(
        api_key=None,
        project_id=None,
        region="us-central1",
        cli_path="gemini",
        timeout=30,
        max_retries=3,
        model_name="gemini-2.0-flash-exp",
        temperature=0.7,
        max_tokens=8192,
        enable_cache=True,
        cache_ttl=3600
    )
    config_manager.save_config(config)
    return config