"""
主入口文件
运行 Gemini CLI Custom Bridge Python MCP 服务器
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from gemini_bridge.server import GeminiBridgeServer
from gemini_bridge.config import get_server_config


async def main():
    """主函数"""
    try:
        # 获取配置
        config = get_server_config()
        
        # 创建并运行服务器
        server = GeminiBridgeServer()
        
        print(f"[MAIN] 启动 Gemini CLI Custom Bridge Python MCP 服务器", file=sys.stderr)
        print(f"[MAIN] 项目根目录: {config.project_root}", file=sys.stderr)
        print(f"[MAIN] 临时目录: {config.temp_dir}", file=sys.stderr)
        print(f"[MAIN] AI API URL: {config.ai_api_url}", file=sys.stderr)
        print(f"[MAIN] AI 模型: {config.ai_model}", file=sys.stderr)
        
        # 运行服务器
        await server.run()
        
    except KeyboardInterrupt:
        print(f"[MAIN] 收到中断信号，正在关闭服务器...", file=sys.stderr)
    except Exception as e:
        print(f"[MAIN] 服务器运行时发生错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())