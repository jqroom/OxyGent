"""
扩展工具模块
包含 grep、glob、edit、web_fetch、web_search、memory 等高级工具
"""

import asyncio
import os
import re
import sys
import json
import glob as python_glob
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse, urljoin
import tempfile

import httpx
import aiofiles

from .path_manager import path_manager
from .config import get_server_config
from .types import (
    GrepArgs,
    GlobArgs,
    EditArgs,
    WebFetchArgs,
    WebSearchArgs,
    MemoryArgs,
    ToolResult,
    GrepResult,
    EditOperation,
    WebContent,
    MemoryEntry,
    PathSecurityError
)


class ExtendedTools:
    """扩展工具类"""
    
    def __init__(self):
        self.config = get_server_config()
        self.memory_file = os.path.join(path_manager.get_config().temp_dir, "memory.json")
        print("[EXTENDED_TOOLS] 扩展工具模块初始化完成", file=sys.stderr)
    
    async def grep(self, args: GrepArgs) -> ToolResult:
        """
        在文件中搜索匹配的行
        
        Args:
            args: grep 参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[GREP] 开始搜索模式: {args.pattern}", file=sys.stderr)
            print(f"[GREP] 搜索路径: {args.path or '.'}", file=sys.stderr)
            
            # 验证路径安全性
            search_path = args.path or "."
            safe_path = path_manager.resolve_safe_path(search_path)
            
            results = []
            
            if os.path.isfile(safe_path):
                # 搜索单个文件
                file_results = await self._grep_file(safe_path, args.pattern, args)
                if file_results:
                    results.extend(file_results)
            elif os.path.isdir(safe_path):
                # 搜索目录
                for root, dirs, files in os.walk(safe_path):
                    # 跳过隐藏目录
                    dirs[:] = [d for d in dirs if not d.startswith('.')]
                    
                    for file in files:
                        # 跳过隐藏文件和不允许的扩展名
                        if file.startswith('.') and file not in self.config.valid_hidden_files:
                            continue
                        
                        file_ext = Path(file).suffix.lower()
                        if file_ext and file_ext not in self.config.allowed_extensions:
                            if file not in self.config.valid_hidden_files:
                                continue
                        
                        file_path = os.path.join(root, file)
                        try:
                            file_results = await self._grep_file(file_path, args.pattern, args)
                            if file_results:
                                results.extend(file_results)
                        except Exception as e:
                            print(f"[GREP] 搜索文件失败 {file_path}: {str(e)}", file=sys.stderr)
                            continue
            else:
                error_msg = f"路径不存在: {search_path}"
                print(f"[GREP] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            print(f"[GREP] 搜索完成，找到 {len(results)} 个匹配", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "grep_results",
                    "pattern": args.pattern,
                    "path": search_path,
                    "matches": [result.dict() for result in results],
                    "total_matches": len(results)
                }]
            )
            
        except PathSecurityError as e:
            error_msg = f"路径安全错误: {str(e)}"
            print(f"[GREP] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"grep 搜索失败: {str(e)}"
            print(f"[GREP] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def _grep_file(self, file_path: str, pattern: str, args: GrepArgs) -> List[GrepResult]:
        """
        在单个文件中搜索
        
        Args:
            file_path: 文件路径
            pattern: 搜索模式
            args: grep 参数
            
        Returns:
            匹配结果列表
        """
        results = []
        
        try:
            # 编译正则表达式
            flags = 0
            if args.ignore_case:
                flags |= re.IGNORECASE
            
            regex = re.compile(pattern, flags)
            
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_number = 0
                async for line in f:
                    line_number += 1
                    line = line.rstrip('\n\r')
                    
                    match = regex.search(line)
                    if match:
                        # 计算相对路径
                        relative_path = os.path.relpath(file_path, path_manager.temp_dir)
                        
                        result = GrepResult(
                            file=relative_path,
                            line_number=line_number,
                            line_content=line,
                            match_start=match.start(),
                            match_end=match.end(),
                            matched_text=match.group()
                        )
                        results.append(result)
                        
                        # 如果只需要第一个匹配，则停止
                        if hasattr(args, 'first_match_only') and args.first_match_only:
                            break
            
        except UnicodeDecodeError:
            # 跳过二进制文件
            pass
        except Exception as e:
            print(f"[GREP] 搜索文件 {file_path} 时出错: {str(e)}", file=sys.stderr)
        
        return results
    
    async def glob_search(self, args: GlobArgs) -> ToolResult:
        """
        使用 glob 模式搜索文件
        
        Args:
            args: glob 参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[GLOB] 开始搜索模式: {args.pattern}", file=sys.stderr)
            
            # 验证路径安全性
            if args.base_path:
                safe_base = path_manager.resolve_safe_path(args.base_path)
            else:
                safe_base = path_manager.temp_dir
            
            # 构建完整的搜索模式
            if os.path.isabs(args.pattern):
                # 绝对路径模式，需要确保在安全目录内
                full_pattern = args.pattern
                if not full_pattern.startswith(path_manager.temp_dir):
                    error_msg = f"glob 模式超出安全目录: {args.pattern}"
                    print(f"[GLOB] {error_msg}", file=sys.stderr)
                    return ToolResult(
                        content=[{"error": error_msg}],
                        is_error=True
                    )
            else:
                # 相对路径模式
                full_pattern = os.path.join(safe_base, args.pattern)
            
            # 执行 glob 搜索
            matches = python_glob.glob(full_pattern, recursive=True)
            
            # 过滤结果，确保都在安全目录内
            safe_matches = []
            for match in matches:
                try:
                    # 验证每个匹配的路径
                    resolved_match = os.path.realpath(match)
                    if resolved_match.startswith(os.path.realpath(path_manager.temp_dir)):
                        # 计算相对路径
                        relative_match = os.path.relpath(match, path_manager.temp_dir)
                        
                        # 获取文件信息
                        if os.path.exists(match):
                            stat_info = os.stat(match)
                            file_info = {
                                "path": relative_match,
                                "absolute_path": match,
                                "type": "file" if os.path.isfile(match) else "directory",
                                "size": stat_info.st_size if os.path.isfile(match) else None,
                                "modified": str(stat_info.st_mtime)
                            }
                            safe_matches.append(file_info)
                except Exception as e:
                    print(f"[GLOB] 处理匹配路径失败 {match}: {str(e)}", file=sys.stderr)
                    continue
            
            # 排序结果
            safe_matches.sort(key=lambda x: x["path"])
            
            print(f"[GLOB] 搜索完成，找到 {len(safe_matches)} 个匹配", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "glob_results",
                    "pattern": args.pattern,
                    "base_path": args.base_path or ".",
                    "matches": safe_matches,
                    "total_matches": len(safe_matches)
                }]
            )
            
        except PathSecurityError as e:
            error_msg = f"路径安全错误: {str(e)}"
            print(f"[GLOB] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"glob 搜索失败: {str(e)}"
            print(f"[GLOB] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def edit_file(self, args: EditArgs) -> ToolResult:
        """
        编辑文件内容
        
        Args:
            args: 编辑参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[EDIT] 开始编辑文件: {args.path}", file=sys.stderr)
            
            # 验证路径安全性
            safe_path = path_manager.resolve_safe_path(args.path)
            
            # 检查文件是否存在
            if not os.path.exists(safe_path):
                error_msg = f"文件不存在: {args.path}"
                print(f"[EDIT] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 读取原始内容
            async with aiofiles.open(safe_path, 'r', encoding='utf-8') as f:
                original_lines = (await f.read()).splitlines()
            
            # 应用编辑操作
            modified_lines = original_lines.copy()
            operations_applied = []
            
            for operation in args.operations:
                try:
                    if operation.type == "replace_line":
                        if 1 <= operation.line_number <= len(modified_lines):
                            old_content = modified_lines[operation.line_number - 1]
                            modified_lines[operation.line_number - 1] = operation.new_content
                            operations_applied.append({
                                "type": "replace_line",
                                "line_number": operation.line_number,
                                "old_content": old_content,
                                "new_content": operation.new_content
                            })
                        else:
                            print(f"[EDIT] 警告: 行号超出范围 {operation.line_number}", file=sys.stderr)
                    
                    elif operation.type == "insert_line":
                        if 0 <= operation.line_number <= len(modified_lines):
                            modified_lines.insert(operation.line_number, operation.new_content)
                            operations_applied.append({
                                "type": "insert_line",
                                "line_number": operation.line_number,
                                "new_content": operation.new_content
                            })
                        else:
                            print(f"[EDIT] 警告: 插入位置超出范围 {operation.line_number}", file=sys.stderr)
                    
                    elif operation.type == "delete_line":
                        if 1 <= operation.line_number <= len(modified_lines):
                            deleted_content = modified_lines.pop(operation.line_number - 1)
                            operations_applied.append({
                                "type": "delete_line",
                                "line_number": operation.line_number,
                                "deleted_content": deleted_content
                            })
                        else:
                            print(f"[EDIT] 警告: 删除行号超出范围 {operation.line_number}", file=sys.stderr)
                    
                except Exception as e:
                    print(f"[EDIT] 应用操作失败: {str(e)}", file=sys.stderr)
                    continue
            
            # 写入修改后的内容
            modified_content = '\n'.join(modified_lines)
            async with aiofiles.open(safe_path, 'w', encoding='utf-8') as f:
                await f.write(modified_content)
            
            print(f"[EDIT] 文件编辑完成: {args.path}, 应用了 {len(operations_applied)} 个操作", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "file_edited",
                    "path": args.path,
                    "operations_applied": operations_applied,
                    "original_lines": len(original_lines),
                    "modified_lines": len(modified_lines),
                    "success": True
                }]
            )
            
        except PathSecurityError as e:
            error_msg = f"路径安全错误: {str(e)}"
            print(f"[EDIT] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"编辑文件失败: {str(e)}"
            print(f"[EDIT] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def web_fetch(self, args: WebFetchArgs) -> ToolResult:
        """
        获取网页内容
        
        Args:
            args: 网页获取参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[WEB_FETCH] 开始获取网页: {args.url}", file=sys.stderr)
            
            # 验证 URL
            parsed_url = urlparse(args.url)
            if not parsed_url.scheme or not parsed_url.netloc:
                error_msg = f"无效的 URL: {args.url}"
                print(f"[WEB_FETCH] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            # 设置请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; GeminiBridge/1.0)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
            
            if args.headers:
                headers.update(args.headers)
            
            # 发送 HTTP 请求
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(args.url, headers=headers)
                response.raise_for_status()
                
                # 获取内容类型
                content_type = response.headers.get("content-type", "").lower()
                
                # 处理不同类型的内容
                if "text/" in content_type or "application/json" in content_type:
                    content = response.text
                    encoding = response.encoding or "utf-8"
                else:
                    # 二进制内容
                    content = response.content.hex()
                    encoding = "binary"
                
                # 限制内容大小
                if len(content) > self.config.max_file_size:
                    content = content[:self.config.max_file_size]
                    truncated = True
                else:
                    truncated = False
                
                web_content = WebContent(
                    url=args.url,
                    content=content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    content_type=content_type,
                    encoding=encoding,
                    size=len(content),
                    truncated=truncated
                )
                
                print(f"[WEB_FETCH] 成功获取网页: {args.url}, 状态码: {response.status_code}, 大小: {len(content)}", file=sys.stderr)
                
                return ToolResult(
                    content=[{
                        "type": "web_content",
                        "result": web_content.dict()
                    }]
                )
                
        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP 错误 {e.response.status_code}: {args.url}"
            print(f"[WEB_FETCH] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except httpx.RequestError as e:
            error_msg = f"请求错误: {str(e)}"
            print(f"[WEB_FETCH] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
        except Exception as e:
            error_msg = f"获取网页失败: {str(e)}"
            print(f"[WEB_FETCH] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def web_search(self, args: WebSearchArgs) -> ToolResult:
        """
        网页搜索（简单实现）
        
        Args:
            args: 网页搜索参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[WEB_SEARCH] 开始搜索: {args.query}", file=sys.stderr)
            
            # 注意：这是一个简化的实现
            # 在实际使用中，你可能需要集成真正的搜索 API（如 Google、Bing 等）
            
            error_msg = "网页搜索功能需要配置搜索 API，当前版本暂不支持"
            print(f"[WEB_SEARCH] {error_msg}", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "web_search_results",
                    "query": args.query,
                    "results": [],
                    "message": error_msg
                }],
                is_error=True
            )
            
        except Exception as e:
            error_msg = f"网页搜索失败: {str(e)}"
            print(f"[WEB_SEARCH] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def memory_operation(self, args: MemoryArgs) -> ToolResult:
        """
        内存操作（存储和检索信息）
        
        Args:
            args: 内存操作参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[MEMORY] 执行内存操作: {args.operation}", file=sys.stderr)
            
            # 确保内存文件目录存在
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            
            # 加载现有内存
            memory_data = await self._load_memory()
            
            if args.operation == "store":
                # 存储信息
                entry = MemoryEntry(
                    key=args.key,
                    value=args.value,
                    timestamp=str(asyncio.get_event_loop().time()),
                    tags=args.tags or []
                )
                
                memory_data[args.key] = entry.dict()
                await self._save_memory(memory_data)
                
                print(f"[MEMORY] 存储成功: {args.key}", file=sys.stderr)
                
                return ToolResult(
                    content=[{
                        "type": "memory_stored",
                        "key": args.key,
                        "success": True
                    }]
                )
                
            elif args.operation == "retrieve":
                # 检索信息
                if args.key in memory_data:
                    entry_data = memory_data[args.key]
                    print(f"[MEMORY] 检索成功: {args.key}", file=sys.stderr)
                    
                    return ToolResult(
                        content=[{
                            "type": "memory_retrieved",
                            "key": args.key,
                            "entry": entry_data,
                            "found": True
                        }]
                    )
                else:
                    print(f"[MEMORY] 未找到: {args.key}", file=sys.stderr)
                    
                    return ToolResult(
                        content=[{
                            "type": "memory_retrieved",
                            "key": args.key,
                            "found": False
                        }]
                    )
                    
            elif args.operation == "list":
                # 列出所有内存项
                entries = []
                for key, entry_data in memory_data.items():
                    if not args.tags or any(tag in entry_data.get("tags", []) for tag in args.tags):
                        entries.append({
                            "key": key,
                            "timestamp": entry_data.get("timestamp"),
                            "tags": entry_data.get("tags", [])
                        })
                
                print(f"[MEMORY] 列出 {len(entries)} 个内存项", file=sys.stderr)
                
                return ToolResult(
                    content=[{
                        "type": "memory_list",
                        "entries": entries,
                        "total_count": len(entries)
                    }]
                )
                
            elif args.operation == "delete":
                # 删除信息
                if args.key in memory_data:
                    del memory_data[args.key]
                    await self._save_memory(memory_data)
                    
                    print(f"[MEMORY] 删除成功: {args.key}", file=sys.stderr)
                    
                    return ToolResult(
                        content=[{
                            "type": "memory_deleted",
                            "key": args.key,
                            "success": True
                        }]
                    )
                else:
                    print(f"[MEMORY] 删除失败，未找到: {args.key}", file=sys.stderr)
                    
                    return ToolResult(
                        content=[{
                            "type": "memory_deleted",
                            "key": args.key,
                            "success": False,
                            "error": "Key not found"
                        }]
                    )
            else:
                error_msg = f"不支持的内存操作: {args.operation}"
                print(f"[MEMORY] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
                
        except Exception as e:
            error_msg = f"内存操作失败: {str(e)}"
            print(f"[MEMORY] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def _load_memory(self) -> Dict[str, Any]:
        """
        加载内存数据
        
        Returns:
            内存数据字典
        """
        try:
            if os.path.exists(self.memory_file):
                async with aiofiles.open(self.memory_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            else:
                return {}
        except Exception as e:
            print(f"[MEMORY] 加载内存文件失败: {str(e)}", file=sys.stderr)
            return {}
    
    async def _save_memory(self, memory_data: Dict[str, Any]) -> None:
        """
        保存内存数据
        
        Args:
            memory_data: 要保存的内存数据
        """
        try:
            async with aiofiles.open(self.memory_file, 'w', encoding='utf-8') as f:
                content = json.dumps(memory_data, indent=2, ensure_ascii=False)
                await f.write(content)
        except Exception as e:
            print(f"[MEMORY] 保存内存文件失败: {str(e)}", file=sys.stderr)
            raise