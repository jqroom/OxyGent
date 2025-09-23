"""
统一的路径管理模块
负责管理和验证所有文件操作的路径安全性
确保所有操作都限制在 gemini-cli 沙盒模式的工作目录内

核心规则：
1. 只允许访问和修改 cache_dir/gemini_cli_workspace 目录下的资源
2. 相对路径均相对于 cache_dir/gemini_cli_workspace 目录
3. 绝对路径必须是 cache_dir/gemini_cli_workspace 的子路径
"""

import os
import sys
from pathlib import Path
from typing import Optional

from .types import PathValidationResult, PathValidationOptions, PathSecurityError


class PathConfig:
    """路径配置类"""
    
    def __init__(self):
        # 获取当前文件的目录路径
        current_dir = Path(__file__).parent.absolute()
        
        # OxyGent 项目根目录（/Users/jiangqi147/github/OxyGent）
        self.PROJECT_ROOT = current_dir.parent.parent.parent.parent
        
        # Gemini CLI 沙盒工作目录（在OxyGent项目根目录下）
        self.SANDBOX_DIR = self.PROJECT_ROOT / "cache_dir" / "gemini_cli_workspace"
        
        # 路径分隔符
        self.PATH_SEP = os.sep
    
    @property
    def project_root(self) -> Path:
        """获取项目根目录"""
        return self.PROJECT_ROOT
    
    @property
    def sandbox_dir(self) -> Path:
        """获取 gemini-cli 沙盒目录"""
        return self.SANDBOX_DIR
    
    @property
    def temp_dir(self) -> Path:
        """获取沙盒目录（保持向后兼容）"""
        return self.SANDBOX_DIR
    
    def is_path_allowed(self, path: str) -> bool:
        """
        检查路径是否被允许访问
        
        Args:
            path: 要检查的路径
            
        Returns:
            bool: 如果路径在沙盒目录内则返回True，否则返回False
        """
        result = validate_path(path)
        return result.is_valid


# 全局配置实例
PATH_CONFIG = PathConfig()


def validate_path(
    input_path: str,
    options: Optional[PathValidationOptions] = None
) -> PathValidationResult:
    """
    统一的路径验证函数
    核心逻辑：所有路径都必须在 cache_dir/gemini_cli_workspace 目录内
    
    Args:
        input_path: 输入的路径（可以是相对路径或绝对路径）
        options: 验证选项
        
    Returns:
        路径验证结果
    """
    if options is None:
        options = PathValidationOptions()
    
    print(f"[PATH_MANAGER] 开始验证路径: \"{input_path}\"", file=sys.stderr)
    print(f"[PATH_MANAGER] 项目根目录: \"{PATH_CONFIG.project_root}\"", file=sys.stderr)
    print(f"[PATH_MANAGER] 允许的沙盒目录: \"{PATH_CONFIG.sandbox_dir}\"", file=sys.stderr)
    
    try:
        # 检查是否为绝对路径
        if os.path.isabs(input_path):
            # 绝对路径：直接使用，但必须在 temp 目录内
            absolute_path = Path(input_path).resolve()
            print(f"[PATH_MANAGER] 处理绝对路径: \"{absolute_path}\"", file=sys.stderr)
        else:
            # 相对路径处理
            if input_path in (".", "./"):
                # 当前目录指向沙盒目录
                absolute_path = PATH_CONFIG.sandbox_dir.resolve()
                print(f"[PATH_MANAGER] 当前目录指向沙盒目录: \"{absolute_path}\"", file=sys.stderr)
            else:
                # 清理路径前缀
                clean_path = input_path.lstrip("./")
                
                # 处理不同的路径情况
                if clean_path in ("cache_dir/gemini_cli_workspace", "gemini_cli_workspace"):
                    # 指向沙盒目录本身
                    absolute_path = PATH_CONFIG.sandbox_dir.resolve()
                    print(f"[PATH_MANAGER] 沙盒目录本身: \"{clean_path}\" -> \"{absolute_path}\"", file=sys.stderr)
                elif clean_path.startswith("cache_dir/gemini_cli_workspace/"):
                    # "cache_dir/gemini_cli_workspace/xxx" 相对于项目根目录解析
                    absolute_path = (PATH_CONFIG.project_root / clean_path).resolve()
                    print(f"[PATH_MANAGER] 沙盒子路径，相对于项目根目录解析: \"{clean_path}\" -> \"{absolute_path}\"", file=sys.stderr)
                else:
                    # 其他相对路径相对于沙盒目录解析
                    absolute_path = (PATH_CONFIG.sandbox_dir / clean_path).resolve()
                    print(f"[PATH_MANAGER] 相对路径相对于沙盒目录解析: \"{clean_path}\" -> \"{absolute_path}\"", file=sys.stderr)
        
        print(f"[PATH_MANAGER] 规范化后的路径: \"{absolute_path}\"", file=sys.stderr)
        
        # 检查路径是否在允许的范围内
        normalized_sandbox_dir = PATH_CONFIG.sandbox_dir.resolve()
        
        # 检查路径关系
        try:
            # 使用 relative_to 来检查路径关系
            relative_path = absolute_path.relative_to(normalized_sandbox_dir)
            is_within_sandbox_dir = True
            is_exact_sandbox_dir = str(relative_path) == "."
        except ValueError:
            # 如果 relative_to 抛出 ValueError，说明路径不在沙盒目录内
            is_within_sandbox_dir = False
            is_exact_sandbox_dir = absolute_path == normalized_sandbox_dir
            relative_path = None
        
        print(f"[PATH_MANAGER] 路径验证检查:", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 标准化沙盒目录: {normalized_sandbox_dir}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 目标绝对路径: {absolute_path}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 相对路径: \"{relative_path}\"", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 在沙盒目录内: {is_within_sandbox_dir}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 是沙盒目录本身: {is_exact_sandbox_dir}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 允许访问沙盒目录本身: {options.allow_exact_temp_dir}", file=sys.stderr)
        
        # 验证路径安全性：必须在沙盒目录内或者是沙盒目录本身（如果允许）
        if not is_within_sandbox_dir and not (is_exact_sandbox_dir and options.allow_exact_temp_dir):
            error_message = (
                f"访问被拒绝: 路径必须在 {normalized_sandbox_dir} 目录内。"
                f"尝试访问的路径: {input_path} (解析为: {absolute_path}, 相对路径: {relative_path})"
            )
            print(f"[PATH_MANAGER] 验证失败: {error_message}", file=sys.stderr)
            
            return PathValidationResult(
                is_valid=False,
                absolute_path=str(absolute_path),
                error_message=error_message
            )
        
        print(f"[PATH_MANAGER] 路径验证通过: \"{absolute_path}\"", file=sys.stderr)
        
        return PathValidationResult(
            is_valid=True,
            absolute_path=str(absolute_path)
        )
        
    except Exception as error:
        error_message = f"路径验证过程中发生错误: {error}"
        print(f"[PATH_MANAGER] 验证异常: {error_message}", file=sys.stderr)
        
        return PathValidationResult(
            is_valid=False,
            absolute_path=input_path,
            error_message=error_message
        )


def validate_working_directory(cwd: Optional[str] = None) -> PathValidationResult:
    """
    验证工作目录路径
    
    Args:
        cwd: 工作目录路径（可选，默认使用沙盒目录）
        
    Returns:
        路径验证结果
    """
    print(f"[PATH_MANAGER] 开始验证工作目录: \"{cwd or 'undefined'}\"", file=sys.stderr)
    
    # 如果没有提供工作目录，使用默认的沙盒目录
    work_dir = cwd or "."
    print(f"[PATH_MANAGER] 使用工作目录: \"{work_dir}\"", file=sys.stderr)
    
    return validate_path(work_dir, PathValidationOptions(allow_exact_temp_dir=True))


def resolve_safe_path(
    input_path: str,
    options: Optional[PathValidationOptions] = None
) -> str:
    """
    安全的路径解析函数
    在验证路径安全性后返回绝对路径，如果验证失败则抛出错误
    
    Args:
        input_path: 输入路径
        options: 验证选项
        
    Returns:
        安全的绝对路径
        
    Raises:
        PathSecurityError: 如果路径验证失败
    """
    result = validate_path(input_path, options)
    
    if not result.is_valid:
        raise PathSecurityError(result.error_message or "路径验证失败")
    
    return result.absolute_path


def resolve_safe_working_directory(cwd: Optional[str] = None) -> str:
    """
    安全的工作目录解析函数
    
    Args:
        cwd: 工作目录路径（可选）
        
    Returns:
        安全的工作目录绝对路径
        
    Raises:
        PathSecurityError: 如果路径验证失败
    """
    result = validate_working_directory(cwd)
    
    if not result.is_valid:
        raise PathSecurityError(result.error_message or "工作目录验证失败")
    
    return result.absolute_path


def get_relative_to_temp_dir(absolute_path: str) -> str:
    """
    获取相对于沙盒目录的路径
    
    Args:
        absolute_path: 绝对路径
        
    Returns:
        相对于沙盒目录的路径
    """
    abs_path = Path(absolute_path)
    sandbox_path = PATH_CONFIG.sandbox_dir.resolve()
    
    try:
        return str(abs_path.relative_to(sandbox_path))
    except ValueError:
        # 如果路径不在沙盒目录内，返回绝对路径
        return str(abs_path)


class PathManager:
    """
    路径管理器单例类
    提供统一的路径管理接口
    """
    
    _instance: Optional['PathManager'] = None
    
    def __new__(cls) -> 'PathManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def validate_path(
        self,
        input_path: str,
        options: Optional[PathValidationOptions] = None
    ) -> PathValidationResult:
        """验证路径"""
        return validate_path(input_path, options)
    
    def resolve_safe_path(
        self,
        input_path: str,
        options: Optional[PathValidationOptions] = None
    ) -> str:
        """解析安全路径"""
        return resolve_safe_path(input_path, options)
    
    def validate_working_directory(self, cwd: Optional[str] = None) -> PathValidationResult:
        """验证工作目录"""
        return validate_working_directory(cwd)
    
    def resolve_safe_working_directory(self, cwd: Optional[str] = None) -> str:
        """解析安全工作目录"""
        return resolve_safe_working_directory(cwd)
    
    def get_config(self) -> PathConfig:
        """获取配置"""
        return PATH_CONFIG


# 导出默认实例
path_manager = PathManager()