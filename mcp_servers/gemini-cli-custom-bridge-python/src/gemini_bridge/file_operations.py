"""
文件操作模块
负责处理文件的读取、写入、列表等基础操作
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

import aiofiles
from .path_manager import path_manager
from .config import get_server_config
from .types import (
    ReadFileArgs,
    WriteFileArgs,
    ListFilesArgs,
    ReadManyFilesArgs,
    ToolResult,
    FileInfo,
    FileOperationError,
    PathSecurityError
)


class FileOperations:
    """文件操作类"""
    
    def __init__(self):
        self.config = get_server_config()
        print("[FILE_OPS] 文件操作模块初始化完成", file=sys.stderr)
    
    async def read_file(self, args: ReadFileArgs) -> ToolResult:
        """
        读取文件内容
        
        Args:
            args: 读取文件参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[FILE_OPS] 开始读取文件: {args.path}", file=sys.stderr)
            
            # 验证路径安全性
            safe_path = path_manager.resolve_safe_path(args.path)
            
            # 检查文件是否存在
            if not os.path.exists(safe_path):
                error_msg = f"文件不存在: {args.path}"
                print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 检查是否为文件
            if not os.path.isfile(safe_path):
                error_msg = f"路径不是文件: {args.path}"
                print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 检查文件大小
            file_size = os.path.getsize(safe_path)
            if file_size > self.config.max_file_size:
                error_msg = f"文件过大: {file_size} bytes，最大允许: {self.config.max_file_size} bytes"
                print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 检查文件扩展名
            file_ext = Path(safe_path).suffix.lower()
            if file_ext and file_ext not in self.config.allowed_extensions:
                # 检查是否为允许的隐藏文件
                file_name = Path(safe_path).name
                if file_name not in self.config.valid_hidden_files:
                    error_msg = f"不允许的文件类型: {file_ext}"
                    print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                    return ToolResult(
                        content=[{"error": error_msg}],
                        is_error=True
                    )
            
            # 读取文件内容
            try:
                async with aiofiles.open(safe_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                
                print(f"[FILE_OPS] 成功读取文件: {args.path}, 大小: {len(content)} 字符", file=sys.stderr)
                
                return ToolResult(
                    content=[{
                        "type": "file_content",
                        "path": args.path,
                        "content": content,
                        "size": len(content),
                        "encoding": "utf-8"
                    }]
                )
                
            except UnicodeDecodeError:
                # 尝试二进制读取
                async with aiofiles.open(safe_path, 'rb') as f:
                    binary_content = await f.read()
                
                print(f"[FILE_OPS] 以二进制模式读取文件: {args.path}, 大小: {len(binary_content)} bytes", file=sys.stderr)
                
                return ToolResult(
                    content=[{
                        "type": "binary_file_content",
                        "path": args.path,
                        "content": binary_content.hex(),  # 转换为十六进制字符串
                        "size": len(binary_content),
                        "encoding": "binary"
                    }]
                )
                
        except PathSecurityError as e:
            error_msg = f"路径安全错误: {str(e)}"
            print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"读取文件失败: {str(e)}"
            print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def write_file(self, args: WriteFileArgs) -> ToolResult:
        """
        写入文件内容
        
        Args:
            args: 写入文件参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[FILE_OPS] 开始写入文件: {args.path}", file=sys.stderr)
            print(f"[FILE_OPS] 内容长度: {len(args.content)} 字符", file=sys.stderr)
            
            # 验证路径安全性
            safe_path = path_manager.resolve_safe_path(args.path)
            
            # 检查内容大小
            content_size = len(args.content.encode('utf-8'))
            if content_size > self.config.max_file_size:
                error_msg = f"内容过大: {content_size} bytes，最大允许: {self.config.max_file_size} bytes"
                print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 检查文件扩展名
            file_ext = Path(safe_path).suffix.lower()
            if file_ext and file_ext not in self.config.allowed_extensions:
                # 检查是否为允许的隐藏文件
                file_name = Path(safe_path).name
                if file_name not in self.config.valid_hidden_files:
                    error_msg = f"不允许写入的文件类型: {file_ext}"
                    print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                    return ToolResult(
                        content=[{"error": error_msg}],
                        is_error=True
                    )
            
            # 确保目录存在
            parent_dir = Path(safe_path).parent
            parent_dir.mkdir(parents=True, exist_ok=True)
            
            # 写入文件
            async with aiofiles.open(safe_path, 'w', encoding='utf-8') as f:
                await f.write(args.content)
            
            # 验证写入结果
            actual_size = os.path.getsize(safe_path)
            
            print(f"[FILE_OPS] 成功写入文件: {args.path}, 大小: {actual_size} bytes", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "file_written",
                    "path": args.path,
                    "size": actual_size,
                    "success": True
                }]
            )
            
        except PathSecurityError as e:
            error_msg = f"路径安全错误: {str(e)}"
            print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"写入文件失败: {str(e)}"
            print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def list_files(self, args: ListFilesArgs) -> ToolResult:
        """
        列出目录中的文件
        
        Args:
            args: 列出文件参数
            
        Returns:
            工具执行结果
        """
        try:
            # 使用默认路径或提供的路径
            target_path = args.path or "."
            print(f"[FILE_OPS] 开始列出目录: {target_path}", file=sys.stderr)
            
            # 验证路径安全性
            safe_path = path_manager.resolve_safe_path(target_path)
            
            # 检查路径是否存在
            if not os.path.exists(safe_path):
                error_msg = f"目录不存在: {target_path}"
                print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 检查是否为目录
            if not os.path.isdir(safe_path):
                error_msg = f"路径不是目录: {target_path}"
                print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 列出文件和目录
            files = []
            directories = []
            
            for item_name in os.listdir(safe_path):
                item_path = os.path.join(safe_path, item_name)
                
                # 跳过隐藏文件（除非在允许列表中）
                if item_name.startswith('.') and item_name not in self.config.valid_hidden_files:
                    continue
                
                try:
                    stat_info = os.stat(item_path)
                    
                    if os.path.isfile(item_path):
                        # 检查文件扩展名
                        file_ext = Path(item_path).suffix.lower()
                        if file_ext and file_ext not in self.config.allowed_extensions:
                            if item_name not in self.config.valid_hidden_files:
                                continue
                        
                        files.append(FileInfo(
                            name=item_name,
                            type="file",
                            size=stat_info.st_size,
                            modified=str(stat_info.st_mtime)
                        ))
                    elif os.path.isdir(item_path):
                        directories.append(FileInfo(
                            name=item_name,
                            type="directory",
                            modified=str(stat_info.st_mtime)
                        ))
                        
                except (OSError, PermissionError):
                    # 跳过无法访问的文件
                    continue
            
            # 按名称排序
            files.sort(key=lambda x: x.name.lower())
            directories.sort(key=lambda x: x.name.lower())
            
            all_items = directories + files
            
            print(f"[FILE_OPS] 成功列出目录: {target_path}, 找到 {len(all_items)} 个项目", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "directory_listing",
                    "path": target_path,
                    "items": [item.dict() for item in all_items],
                    "total_count": len(all_items),
                    "file_count": len(files),
                    "directory_count": len(directories)
                }]
            )
            
        except PathSecurityError as e:
            error_msg = f"路径安全错误: {str(e)}"
            print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"列出文件失败: {str(e)}"
            print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def read_many_files(self, args: ReadManyFilesArgs) -> ToolResult:
        """
        批量读取文件
        
        Args:
            args: 批量读取文件参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[FILE_OPS] 开始批量读取 {len(args.paths)} 个文件", file=sys.stderr)
            
            results = []
            errors = []
            
            for file_path in args.paths:
                try:
                    # 读取单个文件
                    read_args = ReadFileArgs(path=file_path)
                    result = await self.read_file(read_args)
                    
                    if result.is_error:
                        errors.append({
                            "path": file_path,
                            "error": result.content[0].get("error", "未知错误")
                        })
                    else:
                        file_content = result.content[0]
                        
                        if args.include_path_in_response:
                            file_content["original_path"] = file_path
                        
                        results.append(file_content)
                        
                except Exception as e:
                    errors.append({
                        "path": file_path,
                        "error": f"读取失败: {str(e)}"
                    })
            
            print(f"[FILE_OPS] 批量读取完成: 成功 {len(results)} 个，失败 {len(errors)} 个", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "batch_file_read",
                    "successful_reads": results,
                    "failed_reads": errors,
                    "total_requested": len(args.paths),
                    "successful_count": len(results),
                    "failed_count": len(errors)
                }],
                is_error=len(errors) > 0 and len(results) == 0  # 只有全部失败才标记为错误
            )
            
        except Exception as e:
            error_msg = f"批量读取文件失败: {str(e)}"
            print(f"[FILE_OPS] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )