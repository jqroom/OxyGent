"""
Gemini CLI 包装器
负责管理和调用 Gemini CLI 进程
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import psutil
import aiofiles

from .types import BridgeConfig, GeminiRequest, GeminiResponse, ToolResult
from .config_manager import ConfigManager
from .api_proxy import ApiProxy


class GeminiWrapper:
    """Gemini CLI 包装器"""
    
    def __init__(self, config: BridgeConfig):
        """
        初始化 Gemini CLI 包装器
        
        Args:
            config: 桥接配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager()
        self.api_proxy: Optional[ApiProxy] = None
        self.proxy_task: Optional[asyncio.Task] = None
        
        # 初始化环境
        self._setup_environment()
    
    def _setup_environment(self) -> None:
        """设置环境"""
        try:
            # 确保必要的目录存在
            self.config_manager.ensure_directories()
            
            # 保存 Gemini CLI 设置
            self.config_manager.save_gemini_settings()
            
            self.logger.info("Gemini CLI 环境设置完成")
            
        except Exception as e:
            self.logger.error(f"设置 Gemini CLI 环境失败: {e}")
            raise
    
    async def start_proxy(self) -> None:
        """启动 API 代理"""
        if self.api_proxy is None:
            self.api_proxy = ApiProxy(self.config)
            await self.api_proxy.start()
            self.logger.info("API 代理已启动")
    
    async def stop_proxy(self) -> None:
        """停止 API 代理"""
        if self.api_proxy:
            await self.api_proxy.stop()
            self.api_proxy = None
            self.logger.info("API 代理已停止")
    
    def _get_gemini_env(self) -> Dict[str, str]:
        """获取 Gemini CLI 运行环境变量"""
        env = os.environ.copy()
        
        # 添加自定义环境变量
        custom_env = self.config_manager.get_gemini_env_vars()
        env.update(custom_env)
        
        # 如果启用了代理，设置代理 URL
        if self.api_proxy:
            proxy_url = self.api_proxy.get_proxy_url()
            env["GEMINI_BASE_URL"] = proxy_url
        
        return env
    
    def _build_command(self, request: GeminiRequest) -> List[str]:
        """构建 Gemini CLI 命令"""
        cmd = [self.config.gemini_cli_path]
        
        # 添加基础参数
        if self.config.gemini_cli_args:
            cmd.extend(self.config.gemini_cli_args.split())
        
        # 根据请求类型添加特定参数
        if request.command == "chat":
            # 对于聊天命令，直接使用 prompt 作为位置参数
            if request.prompt:
                cmd.append(request.prompt)
        
        elif request.command == "analyze":
            cmd.append("analyze")
            if request.files:
                for file_path in request.files:
                    cmd.extend(["--file", file_path])
        
        elif request.command == "generate":
            cmd.append("generate")
            if request.prompt:
                cmd.extend(["--prompt", request.prompt])
        
        elif request.command == "file":
            cmd.append("file")
            if request.files:
                cmd.extend(request.files)
        
        elif request.command == "tools":
            cmd.append("tools")
        
        elif request.command == "exec":
            # 执行系统命令
            if request.prompt:
                cmd.append(request.prompt)
        
        else:
            # 自定义命令或直接的 prompt
            if request.prompt:
                cmd.append(request.prompt)
        
        # 只添加 Gemini CLI 支持的参数
        if request.args:
            supported_args = {
                'model': 'm',
                'prompt': 'p',
                'prompt-interactive': 'i',
                'sandbox': 's',
                'debug': 'd',
                'all-files': 'a',
                'yolo': 'y',
                'checkpointing': 'c',
                'version': 'v',
                'help': 'h'
            }
            
            for key, value in request.args.items():
                if key in supported_args and value is not None:
                    if isinstance(value, bool):
                        if value:  # 只在值为 True 时添加布尔标志
                            cmd.append(f"--{key}")
                    else:
                        cmd.extend([f"--{key}", str(value)])
        
        return cmd
    
    async def execute_command(self, request: GeminiRequest) -> GeminiResponse:
        """执行 Gemini CLI 命令"""
        try:
            # 构建命令
            cmd = self._build_command(request)
            
            # 准备环境
            env = self._get_gemini_env()
            
            # 设置工作目录
            working_dir = request.working_dir or self.config.gemini_cli_workspace
            
            self.logger.info(f"执行命令: {' '.join(cmd)}")
            self.logger.debug(f"工作目录: {working_dir}")
            
            # 执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=working_dir
            )
            
            # 等待命令完成
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.bridge_timeout
            )
            
            # 处理结果
            success = process.returncode == 0
            output = stdout.decode('utf-8') if stdout else ""
            error = stderr.decode('utf-8') if stderr else None
            
            if not success and not error:
                error = f"命令执行失败，返回码: {process.returncode}"
            
            # 尝试解析 JSON 输出
            metadata = None
            if output and output.strip().startswith('{'):
                try:
                    metadata = json.loads(output)
                except json.JSONDecodeError:
                    pass
            
            response = GeminiResponse(
                success=success,
                output=output,
                error=error,
                metadata=metadata
            )
            
            self.logger.info(f"命令执行完成: success={success}")
            if not success:
                self.logger.error(f"命令执行错误: {error}")
            
            return response
            
        except asyncio.TimeoutError:
            self.logger.error(f"命令执行超时: {self.config.bridge_timeout}秒")
            return GeminiResponse(
                success=False,
                error=f"命令执行超时: {self.config.bridge_timeout}秒"
            )
            
        except Exception as e:
            self.logger.error(f"执行命令失败: {e}")
            return GeminiResponse(
                success=False,
                error=f"执行命令失败: {str(e)}"
            )
    
    async def chat(self, message: str, files: Optional[List[str]] = None, 
                   context: Optional[str] = None) -> ToolResult:
        """聊天功能"""
        try:
            request = GeminiRequest(
                command="chat",
                prompt=message,
                files=files,
                args={"context": context} if context else None
            )
            
            response = await self.execute_command(request)
            
            return ToolResult(
                success=response.success,
                content=response.output,
                error=response.error,
                metadata=response.metadata
            )
            
        except Exception as e:
            self.logger.error(f"聊天失败: {e}")
            return ToolResult(
                success=False,
                error=f"聊天失败: {str(e)}"
            )
    
    async def analyze_code(self, target: str, analysis_type: str = "comprehensive",
                          focus: Optional[str] = None) -> ToolResult:
        """代码分析功能"""
        try:
            args = {"type": analysis_type}
            if focus:
                args["focus"] = focus
            
            # 检查目标是文件还是代码
            if os.path.exists(target):
                files = [target]
                prompt = None
            else:
                files = None
                prompt = f"分析以下代码:\n{target}"
            
            request = GeminiRequest(
                command="analyze",
                prompt=prompt,
                files=files,
                args=args
            )
            
            response = await self.execute_command(request)
            
            return ToolResult(
                success=response.success,
                content=response.output,
                error=response.error,
                metadata=response.metadata
            )
            
        except Exception as e:
            self.logger.error(f"代码分析失败: {e}")
            return ToolResult(
                success=False,
                error=f"代码分析失败: {str(e)}"
            )
    
    async def file_operations(self, operation: str, path: str, 
                             content: Optional[str] = None,
                             pattern: Optional[str] = None) -> ToolResult:
        """文件操作功能"""
        try:
            args = {"operation": operation}
            if content:
                args["content"] = content
            if pattern:
                args["pattern"] = pattern
            
            request = GeminiRequest(
                command="file",
                files=[path],
                args=args
            )
            
            response = await self.execute_command(request)
            
            return ToolResult(
                success=response.success,
                content=response.output,
                error=response.error,
                metadata=response.metadata
            )
            
        except Exception as e:
            self.logger.error(f"文件操作失败: {e}")
            return ToolResult(
                success=False,
                error=f"文件操作失败: {str(e)}"
            )
    
    async def execute_system_command(self, command: str, 
                                   working_dir: Optional[str] = None,
                                   timeout: Optional[int] = None) -> ToolResult:
        """执行系统命令"""
        try:
            request = GeminiRequest(
                command="exec",
                prompt=command,
                working_dir=working_dir,
                args={"timeout": timeout or 30}
            )
            
            response = await self.execute_command(request)
            
            return ToolResult(
                success=response.success,
                content=response.output,
                error=response.error,
                metadata=response.metadata
            )
            
        except Exception as e:
            self.logger.error(f"执行系统命令失败: {e}")
            return ToolResult(
                success=False,
                error=f"执行系统命令失败: {str(e)}"
            )
    
    async def use_tools(self, tool_name: str, tool_args: Dict[str, Any]) -> ToolResult:
        """使用 Gemini CLI 工具"""
        try:
            request = GeminiRequest(
                command="tools",
                args={"tool": tool_name, **tool_args}
            )
            
            response = await self.execute_command(request)
            
            return ToolResult(
                success=response.success,
                content=response.output,
                error=response.error,
                metadata=response.metadata
            )
            
        except Exception as e:
            self.logger.error(f"使用工具失败: {e}")
            return ToolResult(
                success=False,
                error=f"使用工具失败: {str(e)}"
            )
    
    async def custom_operation(self, operation: str, 
                              parameters: Dict[str, Any]) -> ToolResult:
        """自定义操作"""
        try:
            request = GeminiRequest(
                command=operation,
                args=parameters
            )
            
            response = await self.execute_command(request)
            
            return ToolResult(
                success=response.success,
                content=response.output,
                error=response.error,
                metadata=response.metadata
            )
            
        except Exception as e:
            self.logger.error(f"自定义操作失败: {e}")
            return ToolResult(
                success=False,
                error=f"自定义操作失败: {str(e)}"
            )
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            request = GeminiRequest(
                command="version"
            )
            
            response = await self.execute_command(request)
            return response.success
            
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "gemini_cli_path": self.config.gemini_cli_path,
            "workspace": self.config.gemini_cli_workspace,
            "config_dir": self.config.gemini_cli_config_dir,
            "proxy_running": self.api_proxy is not None,
            "proxy_url": self.api_proxy.get_proxy_url() if self.api_proxy else None,
        }


# 用于独立测试的函数
async def test_gemini_wrapper():
    """测试 Gemini 包装器"""
    from .config_manager import ConfigManager
    
    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # 创建包装器
    wrapper = GeminiWrapper(config)
    
    try:
        # 启动代理
        await wrapper.start_proxy()
        
        # 测试聊天
        result = await wrapper.chat("Hello, how are you?")
        print(f"聊天结果: {result}")
        
        # 健康检查
        health = await wrapper.health_check()
        print(f"健康状态: {health}")
        
    finally:
        # 停止代理
        await wrapper.stop_proxy()


if __name__ == "__main__":
    asyncio.run(test_gemini_wrapper())