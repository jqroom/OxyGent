"""
统一的路径管理模块
负责管理和验证所有文件操作的路径安全性
确保所有操作都限制在 autodev 项目根目录下的 temp 目录内

核心规则：
1. 只允许访问和修改 autodev/temp 目录下的资源
2. 相对路径均相对于 autodev/temp 目录
3. 绝对路径必须是 autodev/temp 的子路径
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
        
        # AutoDev 项目根目录（gemini-cli-custom-bridge-python 的上级目录）
        self.PROJECT_ROOT = current_dir.parent.parent.parent
        
        # 允许操作的 temp 目录
        self.TEMP_DIR = self.PROJECT_ROOT / "temp"
        
        # 路径分隔符
        self.PATH_SEP = os.sep
    
    @property
    def project_root(self) -> Path:
        """获取项目根目录"""
        return self.PROJECT_ROOT
    
    @property
    def temp_dir(self) -> Path:
        """获取 temp 目录"""
        return self.TEMP_DIR


# 全局配置实例
PATH_CONFIG = PathConfig()


def validate_path(
    input_path: str,
    options: Optional[PathValidationOptions] = None
) -> PathValidationResult:
    """
    统一的路径验证函数
    核心逻辑：所有路径都必须在 autodev/temp 目录内
    
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
    print(f"[PATH_MANAGER] 允许的temp目录: \"{PATH_CONFIG.temp_dir}\"", file=sys.stderr)
    
    try:
        # 检查是否为绝对路径
        if os.path.isabs(input_path):
            # 绝对路径：直接使用，但必须在 temp 目录内
            absolute_path = Path(input_path).resolve()
            print(f"[PATH_MANAGER] 处理绝对路径: \"{absolute_path}\"", file=sys.stderr)
        else:
            # 相对路径处理
            if input_path in (".", "./"):
                # 当前目录指向 temp 目录
                absolute_path = PATH_CONFIG.temp_dir.resolve()
                print(f"[PATH_MANAGER] 当前目录指向temp目录: \"{absolute_path}\"", file=sys.stderr)
            else:
                # 清理路径前缀
                clean_path = input_path.lstrip("./")
                
                # 修复路径解析逻辑：区分不同的temp路径情况
                if clean_path == "temp":
                    # "./temp" 或 "temp" 应该指向temp目录本身
                    absolute_path = PATH_CONFIG.temp_dir.resolve()
                    print(f"[PATH_MANAGER] temp目录本身: \"{clean_path}\" -> \"{absolute_path}\"", file=sys.stderr)
                elif clean_path.startswith("temp/"):
                    # "temp/xxx" 应该指向temp目录下的子路径
                    absolute_path = (PATH_CONFIG.project_root / clean_path).resolve()
                    print(f"[PATH_MANAGER] temp子路径，相对于项目根目录解析: \"{clean_path}\" -> \"{absolute_path}\"", file=sys.stderr)
                else:
                    # 其他相对路径相对于 temp 目录解析
                    absolute_path = (PATH_CONFIG.temp_dir / clean_path).resolve()
                    print(f"[PATH_MANAGER] 相对路径相对于temp目录解析: \"{clean_path}\" -> \"{absolute_path}\"", file=sys.stderr)
        
        print(f"[PATH_MANAGER] 规范化后的路径: \"{absolute_path}\"", file=sys.stderr)
        
        # 检查路径是否在允许的范围内
        normalized_temp_dir = PATH_CONFIG.temp_dir.resolve()
        
        # 检查路径关系
        try:
            # 使用 relative_to 来检查路径关系
            relative_path = absolute_path.relative_to(normalized_temp_dir)
            is_within_temp_dir = True
            is_exact_temp_dir = str(relative_path) == "."
        except ValueError:
            # 如果 relative_to 抛出 ValueError，说明路径不在 temp 目录内
            is_within_temp_dir = False
            is_exact_temp_dir = absolute_path == normalized_temp_dir
            relative_path = None
        
        print(f"[PATH_MANAGER] 路径验证检查:", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 标准化temp目录: {normalized_temp_dir}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 目标绝对路径: {absolute_path}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 相对路径: \"{relative_path}\"", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 在temp目录内: {is_within_temp_dir}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 是temp目录本身: {is_exact_temp_dir}", file=sys.stderr)
        print(f"[PATH_MANAGER]   - 允许访问temp目录本身: {options.allow_exact_temp_dir}", file=sys.stderr)
        
        # 验证路径安全性：必须在 temp 目录内或者是 temp 目录本身（如果允许）
        if not is_within_temp_dir and not (is_exact_temp_dir and options.allow_exact_temp_dir):
            error_message = (
                f"访问被拒绝: 路径必须在 {normalized_temp_dir} 目录内。"
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
        cwd: 工作目录路径（可选，默认使用 temp 目录）
        
    Returns:
        路径验证结果
    """
    print(f"[PATH_MANAGER] 开始验证工作目录: \"{cwd or 'undefined'}\"", file=sys.stderr)
    
    # 如果没有提供工作目录，使用默认的 temp 目录
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
    获取相对于 temp 目录的路径
    
    Args:
        absolute_path: 绝对路径
        
    Returns:
        相对于 temp 目录的路径
    """
    abs_path = Path(absolute_path)
    temp_path = PATH_CONFIG.temp_dir.resolve()
    
    try:
        return str(abs_path.relative_to(temp_path))
    except ValueError:
        # 如果路径不在 temp 目录内，返回绝对路径
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