"""
Gemini CLI Bridge MCP 服务器主入口
"""

import asyncio
import logging
import sys
from pathlib import Path

from .server import main


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )


if __name__ == "__main__":
    # 设置日志
    setup_logging()
    
    # 运行服务器
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("服务器已停止")
    except Exception as e:
        logging.error(f"服务器运行失败: {e}")
        sys.exit(1)