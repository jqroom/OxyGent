"""
API 代理服务器
负责拦截和转发 Gemini CLI 的 API 请求到自定义接口
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
import httpx
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response, Application
import aiohttp

from .types import BridgeConfig, ApiProxyRequest, ApiProxyResponse


class ApiProxy:
    """API 代理服务器"""
    
    def __init__(self, config: BridgeConfig):
        """
        初始化 API 代理
        
        Args:
            config: 桥接配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.app: Optional[Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
    async def start(self) -> None:
        """启动代理服务器"""
        try:
            # 创建应用
            self.app = web.Application()
            
            # 添加路由
            self.app.router.add_route('*', '/{path:.*}', self.proxy_handler)
            
            # 创建运行器
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # 创建站点
            self.site = web.TCPSite(
                self.runner,
                self.config.api_proxy_host,
                self.config.api_proxy_port
            )
            
            await self.site.start()
            
            self.logger.info(
                f"API 代理服务器已启动: "
                f"http://{self.config.api_proxy_host}:{self.config.api_proxy_port}"
            )
            
        except Exception as e:
            self.logger.error(f"启动 API 代理服务器失败: {e}")
            raise
    
    async def stop(self) -> None:
        """停止代理服务器"""
        try:
            if self.site:
                await self.site.stop()
                self.site = None
                
            if self.runner:
                await self.runner.cleanup()
                self.runner = None
                
            self.app = None
            
            self.logger.info("API 代理服务器已停止")
            
        except Exception as e:
            self.logger.error(f"停止 API 代理服务器失败: {e}")
    
    async def proxy_handler(self, request: Request) -> Response:
        """代理请求处理器"""
        try:
            # 记录请求信息
            self.logger.debug(f"代理请求: {request.method} {request.url}")
            
            # 检查是否是 Gemini API 请求
            if self._is_gemini_api_request(request):
                return await self._handle_gemini_api_request(request)
            else:
                return await self._handle_other_request(request)
                
        except Exception as e:
            self.logger.error(f"代理请求处理失败: {e}")
            return web.Response(
                status=500,
                text=json.dumps({"error": f"代理错误: {str(e)}"}),
                content_type="application/json"
            )
    
    def _is_gemini_api_request(self, request: Request) -> bool:
        """检查是否是 Gemini API 请求"""
        # 检查 URL 路径
        path = str(request.url.path)
        gemini_patterns = [
            "/v1/models",
            "/v1/chat/completions",
            "/v1/completions",
            "/v1beta/models",
            "/v1beta/generateContent",
        ]
        
        for pattern in gemini_patterns:
            if pattern in path:
                return True
        
        # 检查请求头
        user_agent = request.headers.get("User-Agent", "")
        if "gemini" in user_agent.lower():
            return True
        
        return False
    
    async def _handle_gemini_api_request(self, request: Request) -> Response:
        """处理 Gemini API 请求"""
        try:
            # 读取请求体
            body = await request.read()
            
            # 构建目标 URL
            target_url = self._build_target_url(request)
            
            # 准备请求头
            headers = self._prepare_headers(request)
            
            # 发送请求到自定义 API
            async with ClientSession() as session:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=body,
                    timeout=aiohttp.ClientTimeout(total=self.config.bridge_timeout)
                ) as response:
                    
                    # 读取响应
                    response_body = await response.read()
                    
                    # 处理响应
                    processed_response = await self._process_response(
                        response, response_body
                    )
                    
                    return processed_response
                    
        except Exception as e:
            self.logger.error(f"处理 Gemini API 请求失败: {e}")
            return web.Response(
                status=500,
                text=json.dumps({"error": f"API 请求失败: {str(e)}"}),
                content_type="application/json"
            )
    
    async def _handle_other_request(self, request: Request) -> Response:
        """处理其他请求（直接转发）"""
        try:
            # 构建原始目标 URL
            original_url = str(request.url).replace(
                f"http://{self.config.api_proxy_host}:{self.config.api_proxy_port}",
                "https://generativelanguage.googleapis.com"
            )
            
            # 读取请求体
            body = await request.read()
            
            # 准备请求头
            headers = dict(request.headers)
            headers.pop("Host", None)  # 移除 Host 头
            
            # 转发请求
            async with ClientSession() as session:
                async with session.request(
                    method=request.method,
                    url=original_url,
                    headers=headers,
                    data=body,
                    timeout=aiohttp.ClientTimeout(total=self.config.bridge_timeout)
                ) as response:
                    
                    # 读取响应
                    response_body = await response.read()
                    
                    # 返回响应
                    return web.Response(
                        status=response.status,
                        body=response_body,
                        headers=response.headers,
                        content_type=response.content_type
                    )
                    
        except Exception as e:
            self.logger.error(f"转发请求失败: {e}")
            return web.Response(
                status=500,
                text=json.dumps({"error": f"转发失败: {str(e)}"}),
                content_type="application/json"
            )
    
    def _build_target_url(self, request: Request) -> str:
        """构建目标 URL"""
        # 获取原始路径和查询参数
        path = str(request.url.path)
        query = request.url.query_string if request.url.query_string else ""
        
        # 构建完整的目标 URL
        target_url = self.config.custom_ai_api_url.rstrip('/')
        
        # 添加路径
        if not path.startswith('/'):
            path = '/' + path
        target_url += path
        
        # 添加查询参数
        if query:
            target_url += '?' + query
        
        return target_url
    
    def _prepare_headers(self, request: Request) -> Dict[str, str]:
        """准备请求头"""
        headers = dict(request.headers)
        
        # 移除代理相关的头
        headers.pop("Host", None)
        headers.pop("Connection", None)
        
        # 添加自定义 API 密钥
        if "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.config.custom_ai_api_key}"
        
        # 确保内容类型
        if request.content_type and "Content-Type" not in headers:
            headers["Content-Type"] = request.content_type
        
        return headers
    
    async def _process_response(self, response: aiohttp.ClientResponse, body: bytes) -> Response:
        """处理响应"""
        try:
            # 尝试解析 JSON 响应
            if response.content_type and "json" in response.content_type:
                try:
                    response_data = json.loads(body.decode('utf-8'))
                    
                    # 转换响应格式（如果需要）
                    converted_data = self._convert_response_format(response_data)
                    
                    return web.Response(
                        status=response.status,
                        text=json.dumps(converted_data, ensure_ascii=False),
                        content_type="application/json"
                    )
                    
                except json.JSONDecodeError:
                    pass
            
            # 返回原始响应
            return web.Response(
                status=response.status,
                body=body,
                headers=response.headers,
                content_type=response.content_type
            )
            
        except Exception as e:
            self.logger.error(f"处理响应失败: {e}")
            return web.Response(
                status=500,
                text=json.dumps({"error": f"响应处理失败: {str(e)}"}),
                content_type="application/json"
            )
    
    def _convert_response_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """转换响应格式（如果需要适配 Gemini 格式）"""
        # 这里可以添加响应格式转换逻辑
        # 例如，将其他 API 的响应格式转换为 Gemini 期望的格式
        
        # 目前直接返回原始数据
        return data
    
    async def health_check(self) -> bool:
        """健康检查"""
        try:
            if not self.site:
                return False
            
            # 简单的健康检查
            async with ClientSession() as session:
                async with session.get(
                    f"http://{self.config.api_proxy_host}:{self.config.api_proxy_port}/health",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
                    
        except Exception:
            return False
    
    def get_proxy_url(self) -> str:
        """获取代理 URL"""
        return f"http://{self.config.api_proxy_host}:{self.config.api_proxy_port}"


# 用于独立运行代理服务器的函数
async def run_proxy_server(config: BridgeConfig) -> None:
    """运行代理服务器"""
    proxy = ApiProxy(config)
    
    try:
        await proxy.start()
        
        # 保持运行
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logging.info("收到中断信号，正在停止代理服务器...")
    finally:
        await proxy.stop()


if __name__ == "__main__":
    # 用于测试的简单配置
    from .config_manager import ConfigManager
    
    # 加载配置
    config_manager = ConfigManager()
    config = config_manager.get_config()
    
    # 运行代理服务器
    asyncio.run(run_proxy_server(config))