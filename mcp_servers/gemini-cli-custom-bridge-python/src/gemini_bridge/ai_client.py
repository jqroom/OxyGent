"""
AI 客户端模块
负责与自定义 AI API 进行通信
"""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional, AsyncIterator

import httpx
from .config import get_ai_config
from .types import (
    ChatCompletionArgs,
    CodeAnalysisArgs,
    ChatCompletionResponse,
    StreamChunk,
    ToolResult,
    AIAPIError,
    ChatMessage
)


class AIClient:
    """AI 客户端"""
    
    def __init__(self):
        self.config = get_ai_config()
        self.client = httpx.AsyncClient(timeout=30.0)
        
        print("[AI_CLIENT] AI 客户端初始化完成", file=sys.stderr)
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.client.aclose()
    
    async def chat_completion(self, args: ChatCompletionArgs) -> ToolResult:
        """
        聊天完成
        
        Args:
            args: 聊天完成参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[AI_CLIENT] 开始聊天完成请求", file=sys.stderr)
            print(f"[AI_CLIENT] 消息数量: {len(args.messages)}", file=sys.stderr)
            print(f"[AI_CLIENT] 流式响应: {args.stream}", file=sys.stderr)
            
            # 准备请求数据
            request_data = {
                "model": args.model or self.config.model,
                "messages": [msg.dict() for msg in args.messages],
                "temperature": args.temperature or self.config.temperature,
                "max_tokens": args.max_tokens or self.config.max_tokens,
                "stream": args.stream or False
            }
            
            print(f"[AI_CLIENT] 请求数据: {json.dumps(request_data, ensure_ascii=False)}", file=sys.stderr)
            
            # 准备请求头
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}"
            }
            
            if args.stream:
                # 流式响应处理
                return await self._handle_stream_response(request_data, headers)
            else:
                # 非流式响应处理
                return await self._handle_normal_response(request_data, headers)
                
        except Exception as e:
            error_msg = f"聊天完成请求失败: {str(e)}"
            print(f"[AI_CLIENT] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def analyze_code(self, args: CodeAnalysisArgs) -> ToolResult:
        """
        代码分析
        
        Args:
            args: 代码分析参数
            
        Returns:
            工具执行结果
        """
        try:
            print(f"[AI_CLIENT] 开始代码分析请求", file=sys.stderr)
            print(f"[AI_CLIENT] 代码长度: {len(args.code)} 字符", file=sys.stderr)
            print(f"[AI_CLIENT] 分析类型: {args.analysis_type}", file=sys.stderr)
            
            # 构建分析提示词
            analysis_prompts = {
                "review": "请对以下代码进行代码审查，指出潜在问题、改进建议和最佳实践：",
                "optimize": "请对以下代码进行性能优化分析，提供具体的优化建议：",
                "explain": "请详细解释以下代码的功能、逻辑和实现原理：",
                "debug": "请分析以下代码中可能存在的bug和错误，提供调试建议："
            }
            
            prompt = analysis_prompts.get(args.analysis_type, analysis_prompts["review"])
            
            # 构建消息
            messages = [
                ChatMessage(role="system", content="你是一个专业的代码分析助手，请提供详细、准确的代码分析。"),
                ChatMessage(
                    role="user", 
                    content=f"{prompt}\n\n```{args.language or 'text'}\n{args.code}\n```"
                )
            ]
            
            # 调用聊天完成
            chat_args = ChatCompletionArgs(
                messages=messages,
                model=self.config.model,
                temperature=0.3,  # 代码分析使用较低的温度
                max_tokens=self.config.max_tokens,
                stream=False
            )
            
            return await self.chat_completion(chat_args)
            
        except Exception as e:
            error_msg = f"代码分析请求失败: {str(e)}"
            print(f"[AI_CLIENT] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def _handle_normal_response(self, request_data: Dict[str, Any], headers: Dict[str, str]) -> ToolResult:
        """处理非流式响应"""
        try:
            print(f"[AI_CLIENT] 发送非流式请求到: {self.config.api_url}", file=sys.stderr)
            
            response = await self.client.post(
                self.config.api_url,
                json=request_data,
                headers=headers
            )
            
            print(f"[AI_CLIENT] 响应状态码: {response.status_code}", file=sys.stderr)
            
            if response.status_code != 200:
                error_msg = f"API 请求失败，状态码: {response.status_code}, 响应: {response.text}"
                print(f"[AI_CLIENT] {error_msg}", file=sys.stderr)
                return ToolResult(
                    content=[{"error": error_msg}],
                    is_error=True
                )
            
            response_data = response.json()
            print(f"[AI_CLIENT] 响应数据: {json.dumps(response_data, ensure_ascii=False)}", file=sys.stderr)
            
            return ToolResult(
                content=[{
                    "type": "chat_completion",
                    "response": response_data
                }]
            )
            
        except Exception as e:
            error_msg = f"处理非流式响应失败: {str(e)}"
            print(f"[AI_CLIENT] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def _handle_stream_response(self, request_data: Dict[str, Any], headers: Dict[str, str]) -> ToolResult:
        """处理流式响应"""
        try:
            print(f"[AI_CLIENT] 发送流式请求到: {self.config.api_url}", file=sys.stderr)
            
            chunks = []
            full_content = ""
            
            async with self.client.stream(
                "POST",
                self.config.api_url,
                json=request_data,
                headers=headers
            ) as response:
                
                print(f"[AI_CLIENT] 流式响应状态码: {response.status_code}", file=sys.stderr)
                
                if response.status_code != 200:
                    error_msg = f"流式 API 请求失败，状态码: {response.status_code}"
                    print(f"[AI_CLIENT] {error_msg}", file=sys.stderr)
                    return ToolResult(
                        content=[{"error": error_msg}],
                        is_error=True
                    )
                
                chunk_index = 0
                async for chunk in response.aiter_lines():
                    if chunk.strip():
                        try:
                            # 处理 SSE 格式的数据
                            if chunk.startswith("data: "):
                                data_str = chunk[6:]  # 移除 "data: " 前缀
                                
                                if data_str.strip() == "[DONE]":
                                    print("[AI_CLIENT] 流式响应完成", file=sys.stderr)
                                    break
                                
                                chunk_data = json.loads(data_str)
                                
                                # 提取内容
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    choice = chunk_data["choices"][0]
                                    if "delta" in choice and "content" in choice["delta"]:
                                        content = choice["delta"]["content"]
                                        full_content += content
                                        
                                        chunks.append({
                                            "type": "stream_chunk",
                                            "chunk_index": chunk_index,
                                            "content": content,
                                            "done": False
                                        })
                                        chunk_index += 1
                                
                        except json.JSONDecodeError as e:
                            print(f"[AI_CLIENT] 解析流式数据失败: {e}, 数据: {chunk}", file=sys.stderr)
                            continue
            
            # 添加完成标记
            chunks.append({
                "type": "stream_complete",
                "full_content": full_content,
                "total_chunks": chunk_index,
                "done": True
            })
            
            print(f"[AI_CLIENT] 流式响应完成，总共 {chunk_index} 个块", file=sys.stderr)
            
            return ToolResult(
                content=chunks
            )
            
        except Exception as e:
            error_msg = f"处理流式响应失败: {str(e)}"
            print(f"[AI_CLIENT] {error_msg}", file=sys.stderr)
            return ToolResult(
                content=[{"error": error_msg}],
                is_error=True
            )
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
        print("[AI_CLIENT] AI 客户端已关闭", file=sys.stderr)