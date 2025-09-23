"""
命令执行模块
负责安全地执行系统命令
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from .path_manager import path_manager
from .config import get_server_config
from .types import (
    ExecuteCommandArgs,
    CommandResult,
    ToolResult,
    PathSecurityError
)


class CommandExecutor:
    """命令执行器"""
    
    def __init__(self):
        self.config = get_server_config()
        print("[CMD_EXECUTOR] 命令执行模块初始化完成", file=sys.stderr)
    
    async def execute_command(self, args: ExecuteCommandArgs) -> ToolResult:
        """
        执行系统命令
        
        Args:
            args: 命令执行参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[CMD_EXECUTOR] 开始执行命令: {args.command}", file=sys.stderr)
            
            # 验证工作目录
            if args.cwd:
                safe_cwd = path_manager.resolve_safe_working_directory(args.cwd)
                print(f"[CMD_EXECUTOR] 使用工作目录: {safe_cwd}", file=sys.stderr)
            else:
                safe_cwd = path_manager.resolve_safe_working_directory()
                print(f"[CMD_EXECUTOR] 使用默认工作目录: {safe_cwd}", file=sys.stderr)
            
            # 检查工作目录是否存在
            if not os.path.exists(safe_cwd):
                error_msg = f"工作目录不存在: {args.cwd or '.'}"
                print(f"[CMD_EXECUTOR] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 安全检查：禁止危险命令
            dangerous_commands = [
                'rm -rf /',
                'sudo rm',
                'format',
                'del /f /s /q',
                'shutdown',
                'reboot',
                'halt',
                'poweroff',
                'mkfs',
                'fdisk',
                'dd if=',
                'chmod 777',
                'chown -R',
                'passwd',
                'su -',
                'sudo su',
                'init 0',
                'init 6'
            ]
            
            command_lower = args.command.lower()
            for dangerous_cmd in dangerous_commands:
                if dangerous_cmd in command_lower:
                    error_msg = f"禁止执行危险命令: {args.command}"
                    print(f"[CMD_EXECUTOR] {error_msg}", file=sys.stderr)
                    return ToolResult(
                        content=[{"error": error_msg}],
                        is_error=True
                    )
            
            # 执行命令
            try:
                print(f"[CMD_EXECUTOR] 在目录 {safe_cwd} 中执行: {args.command}", file=sys.stderr)
                
                process = await asyncio.create_subprocess_shell(
                    args.command,
                    cwd=safe_cwd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=os.environ.copy()
                )
                
                # 等待命令完成（设置超时）
                try:
                    stdout_data, stderr_data = await asyncio.wait_for(
                        process.communicate(),
                        timeout=self.config.timeout
                    )
                except asyncio.TimeoutError:
                    # 超时则终止进程
                    process.terminate()
                    await process.wait()
                    error_msg = f"命令执行超时 ({self.config.timeout}s): {args.command}"
                    print(f"[CMD_EXECUTOR] {error_msg}", file=sys.stderr)
                    return ToolResult(
                        content=[{"error": error_msg}],
                        is_error=True
                    )
                
                # 解码输出
                stdout_text = stdout_data.decode('utf-8', errors='replace') if stdout_data else ""
                stderr_text = stderr_data.decode('utf-8', errors='replace') if stderr_data else ""
                
                exit_code = process.returncode
                success = exit_code == 0
                
                print(f"[CMD_EXECUTOR] 命令执行完成，退出码: {exit_code}", file=sys.stderr)
                print(f"[CMD_EXECUTOR] 标准输出长度: {len(stdout_text)} 字符", file=sys.stderr)
                print(f"[CMD_EXECUTOR] 错误输出长度: {len(stderr_text)} 字符", file=sys.stderr)
                
                # 创建命令结果
                command_result = CommandResult(
                    stdout=stdout_text,
                    stderr=stderr_text,
                    success=success,
                    exit_code=exit_code,
                    working_directory=args.cwd or "."
                )
                
                return ToolResult(
                    content=[{
                        "type": "command_execution",
                        "command": args.command,
                        "result": command_result.dict(),
                        "working_directory": safe_cwd
                    }],
                    is_error=not success
                )
                
            except FileNotFoundError as e:
                error_msg = f"命令未找到: {args.command} ({str(e)})"
                print(f"[CMD_EXECUTOR] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            except PermissionError as e:
                error_msg = f"权限不足: {args.command} ({str(e)})"
                print(f"[CMD_EXECUTOR] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
                
        except PathSecurityError as e:
            error_msg = f"路径安全错误: {str(e)}"
            print(f"[CMD_EXECUTOR] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"执行命令失败: {str(e)}"
            print(f"[CMD_EXECUTOR] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    def _is_safe_command(self, command: str) -> bool:
        """
        检查命令是否安全
        
        Args:
            command: 要检查的命令
            
        Returns:
            是否安全
        """
        # 基本的安全检查
        unsafe_patterns = [
            # 文件系统操作
            'rm -rf',
            'del /f /s /q',
            'format',
            'mkfs',
            'fdisk',
            
            # 系统控制
            'shutdown',
            'reboot',
            'halt',
            'poweroff',
            'init',
            
            # 权限操作
            'chmod 777',
            'chown -R',
            'passwd',
            'su -',
            'sudo',
            
            # 网络操作
            'wget',
            'curl',
            'nc ',
            'netcat',
            
            # 进程操作
            'kill -9',
            'killall',
            'pkill',
        ]
        
        command_lower = command.lower()
        
        for pattern in unsafe_patterns:
            if pattern in command_lower:
                return False
        
        return True
    
    def _sanitize_command(self, command: str) -> str:
        """
        清理命令字符串
        
        Args:
            command: 原始命令
            
        Returns:
            清理后的命令
        """
        # 移除潜在的危险字符
        dangerous_chars = [';', '&&', '||', '|', '>', '>>', '<', '`', '$']
        
        sanitized = command
        for char in dangerous_chars:
            if char in sanitized:
                print(f"[CMD_EXECUTOR] 警告: 命令包含潜在危险字符 '{char}': {command}", file=sys.stderr)
        
        return sanitized.strip()