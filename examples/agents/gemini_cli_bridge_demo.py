"""Demo for using OxyGent with Gemini CLI Bridge MCP Server."""

import asyncio
import logging
import os
from typing import Any, Dict

from oxygent import MAS, Config, oxy
from oxygent.utils.env_utils import get_env_var

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 从环境变量加载配置
def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    try:
        config = {
            "DEFAULT_LLM_API_KEY": get_env_var("DEFAULT_LLM_API_KEY"),
            "DEFAULT_LLM_BASE_URL": get_env_var("DEFAULT_LLM_BASE_URL"),
            "DEFAULT_LLM_MODEL_NAME": get_env_var("DEFAULT_LLM_MODEL_NAME"),
        }
        logger.info(f"Loaded configuration: API_KEY={config['DEFAULT_LLM_API_KEY']}, BASE_URL={config['DEFAULT_LLM_BASE_URL']}, MODEL={config['DEFAULT_LLM_MODEL_NAME']}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        raise


# Gemini CLI Bridge MCP 工具专用系统提示词
GEMINI_BRIDGE_SYSTEM_PROMPT = """
你是一个 Gemini CLI Bridge MCP 工具专家，基于原版 Google Gemini CLI 提供强大的 AI 功能。

**🚀 核心能力**
你可以通过以下工具访问完整的 Gemini CLI 功能集：

1. **gemini_chat**: 与 Gemini 模型进行智能对话
   - 支持多轮对话
   - 上下文理解
   - 自然语言处理

2. **gemini_analyze**: 深度分析各种内容
   - 代码分析和优化建议
   - 文档分析和总结
   - 数据分析和洞察

3. **gemini_file_ops**: 智能文件操作
   - 文件内容理解和处理
   - 批量文件操作
   - 格式转换

4. **gemini_command**: 执行 Gemini CLI 命令
   - 直接访问 Gemini CLI 原生功能
   - 自定义命令执行
   - 高级配置选项

5. **gemini_tools**: 访问 Gemini 内置工具集
   - 专业工具调用
   - 工具链组合
   - 增强功能

6. **gemini_custom**: 自定义功能扩展
   - API 接口自定义
   - 特殊需求处理
   - 扩展能力

**🔧 工具调用格式**：
```json
{
    "think": "分析任务需求和选择工具的原因",
    "tool_name": "具体工具名称",
    "arguments": {
        "参数名": "参数值"
    }
}
```

**💡 使用策略**：
1. **简单对话**：使用 gemini_chat 进行自然对话
2. **代码相关**：使用 gemini_analyze 进行代码分析
3. **文件处理**：使用 gemini_file_ops 处理文件操作
4. **高级功能**：使用 gemini_command 或 gemini_tools
5. **特殊需求**：使用 gemini_custom 处理自定义场景

**✨ 优势特性**：
- 基于原版 Google Gemini CLI，功能完整可靠
- 支持自定义 API 接口配置
- 无需重新实现，直接使用 Gemini CLI 的所有功能
- 高性能异步处理
- 完整的错误处理和日志记录

收到工具响应后，将结果转换为自然、有用的回答。
"""

# Master 智能体系统提示词
MASTER_SYSTEM_PROMPT = """
你是一个 Master 智能体，负责协调和管理 Gemini CLI Bridge 智能体来完成用户任务。

可用的子智能体：
- gemini_bridge_agent: 基于原版 Gemini CLI 的强大 AI 助手，支持对话、分析、文件操作等

对于用户的任何问题或请求，你应该：

1. **AI 对话和问答**：委托给 gemini_bridge_agent 使用 gemini_chat 工具
2. **代码分析和优化**：委托给 gemini_bridge_agent 使用 gemini_analyze 工具  
3. **文件处理任务**：委托给 gemini_bridge_agent 使用 gemini_file_ops 工具
4. **复杂 AI 任务**：委托给 gemini_bridge_agent 使用相应的专业工具

**重要**：Gemini CLI Bridge 提供了完整的 Gemini CLI 功能，可以处理各种复杂的 AI 任务。

当委托给子智能体时，使用以下 JSON 格式：
```json
{
    "think": "分析用户需求和委托策略",
    "tool_name": "gemini_bridge_agent",
    "arguments": {
        "query": "用户的原始问题或请求",
        "task_context": {
            "objective": "明确的任务目标",
            "tool_preference": "建议使用的工具类型",
            "background": "相关背景信息",
            "constraints": "任何限制条件"
        }
    }
}
```

**示例**：
用户说"帮我分析这段 Python 代码"时，应该回应：
```json
{
    "think": "用户需要代码分析，这是 gemini_bridge_agent 的专长，建议使用 gemini_analyze 工具",
    "tool_name": "gemini_bridge_agent", 
    "arguments": {
        "query": "请分析这段 Python 代码",
        "task_context": {
            "objective": "提供代码分析和优化建议",
            "tool_preference": "gemini_analyze",
            "background": "用户提供了 Python 代码需要分析",
            "constraints": "提供专业、详细的分析结果"
        }
    }
}
```

请始终委托给 gemini_bridge_agent，充分利用 Gemini CLI 的强大功能。
"""


class GeminiCliBridgeDemo:
    """Gemini CLI Bridge 演示实现类。"""

    def __init__(self):
        """使用配置初始化 Gemini CLI Bridge 演示。"""
        try:
            self.config = load_config()
            Config.set_agent_llm_model("default_llm")
            self.oxy_space = self._create_oxy_space()
        except Exception as e:
            logger.error(f"Failed to initialize GeminiCliBridgeDemo: {str(e)}")
            raise

    def _create_oxy_space(self) -> list:
        """创建并配置包含所有必需组件的 oxy 空间。"""
        try:
            return [
                self._create_http_llm(),
                self._create_gemini_bridge_tools(),
                self._create_gemini_bridge_agent(),
                self._create_master_agent(),
            ]
        except Exception as e:
            logger.error(f"Failed to create oxy space: {str(e)}")
            raise

    def _create_http_llm(self) -> oxy.HttpLLM:
        """创建并配置 HTTP LLM 组件。"""
        return oxy.HttpLLM(
            name="default_llm",
            api_key=self.config["DEFAULT_LLM_API_KEY"],
            base_url=self.config["DEFAULT_LLM_BASE_URL"],
            model_name=self.config["DEFAULT_LLM_MODEL_NAME"],
            llm_params={"temperature": 0.01},
            semaphore=4,
            category="llm",
            class_name="HttpLLM",
            desc="Default language model",
            desc_for_llm="Default language model for text generation",
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=60,
            retries=3,
            delay=1,
            is_multimodal_supported=False,
        )

    def _create_gemini_bridge_tools(self) -> oxy.StdioMCPClient:
        """创建并配置 Gemini CLI Bridge MCP 客户端。"""
        # 获取当前脚本的绝对路径，然后构建相对于项目根目录的路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        bridge_path = os.path.join(project_root, "mcp_servers", "gemini-cli-bridge")
        
        return oxy.StdioMCPClient(
            name="gemini_bridge_tools",
            params={
                "command": "python",
                "args": ["-m", "gemini_cli_bridge"],
                "cwd": bridge_path,
                "env": {
                    "PATH": os.environ.get("PATH", ""),
                    "CUSTOM_AI_API_URL": "http://llm-32b.jd.com/v1/chat/completions",
                    "CUSTOM_AI_MODEL": "qwen25-32b-native",
                    "CUSTOM_AI_API_KEY": "demo-key-for-testing",
                }
            },
            category="tool",
            class_name="StdioMCPClient",
            desc="Gemini CLI Bridge MCP tools based on original Google Gemini CLI",
            desc_for_llm="Gemini CLI Bridge MCP tools providing complete Gemini CLI functionality with custom API support",
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=30,
            retries=3,
            delay=1,
            friendly_error_text="Gemini CLI Bridge operation failed",
            semaphore=2,
        )

    def _create_gemini_bridge_agent(self) -> oxy.ReActAgent:
        """创建并配置 Gemini CLI Bridge 智能体。"""
        return oxy.ReActAgent(
            name="gemini_bridge_agent",
            desc="Gemini CLI Bridge agent with full Gemini CLI capabilities",
            desc_for_llm="Specialized agent for handling AI tasks using original Gemini CLI through MCP bridge",
            category="agent",
            class_name="ReActAgent",
            tools=["gemini_bridge_tools"],
            llm_model="default_llm",
            prompt=GEMINI_BRIDGE_SYSTEM_PROMPT,
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=30,
            retries=3,
            delay=1,
            is_multimodal_supported=False,
            semaphore=2,
        )

    def _create_master_agent(self) -> oxy.ReActAgent:
        """创建并配置 Master 智能体。"""
        return oxy.ReActAgent(
            name="master_agent",
            desc="Master agent coordinating Gemini CLI Bridge tasks",
            desc_for_llm="Master coordinator for Gemini CLI Bridge operations",
            category="agent",
            class_name="ReActAgent",
            sub_agents=["gemini_bridge_agent"],
            is_master=True,
            llm_model="default_llm",
            prompt=MASTER_SYSTEM_PROMPT,
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=100,
            retries=3,
            delay=1,
            is_multimodal_supported=False,
            semaphore=2,
        )

    async def run_demo(
        self, 
        user_query: str = "你好！请介绍一下你的功能。"
    ):
        """运行 Gemini CLI Bridge 演示。
        
        Args:
            user_query: 用户查询
        """
        try:
            logger.info("🚀 Starting Gemini CLI Bridge Demo...")
            logger.info(f"User Query: {user_query}")
            
            # 使用 MAS 启动 Web 服务
            async with MAS(oxy_space=self.oxy_space) as mas:
                logger.info(f"Starting Gemini CLI Bridge service with query: {user_query}")
                await mas.start_web_service(first_query=user_query, port=8080)
                logger.info("Gemini CLI Bridge service completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Demo failed: {str(e)}")
            raise


async def main():
    """Gemini CLI Bridge 演示的主入口点。"""
    try:
        # 检查环境变量
        try:
            # 检查必需的环境变量
            required_vars = [
                "DEFAULT_LLM_API_KEY",
                "DEFAULT_LLM_BASE_URL", 
                "DEFAULT_LLM_MODEL_NAME"
            ]
            missing_vars = []
            for var in required_vars:
                try:
                    value = get_env_var(var, expected_type=str, default_val="")
                    if not value:
                        missing_vars.append(var)
                except Exception:
                    missing_vars.append(var)
            
            if missing_vars:
                logger.warning("⚠️  警告: 未设置以下环境变量:")
                for var in missing_vars:
                    logger.warning(f"   {var}")
                logger.warning("   请确保在环境中配置这些变量")
                logger.warning("   演示将继续运行，但功能可能受限")
        except Exception as e:
            logger.warning(f"⚠️  警告: 检查环境变量时出错: {str(e)}")
            logger.warning("   演示将继续运行，但功能可能受限")
        
        demo = GeminiCliBridgeDemo()
        await demo.run_demo()
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise


if __name__ == "__main__":
    print("🎯 Gemini CLI Bridge MCP OxyGent 演示")
    print("=" * 50)
    print("📝 使用说明:")
    print("1. 设置必需的环境变量:")
    print("   export DEFAULT_LLM_API_KEY='your-llm-api-key'")
    print("   export DEFAULT_LLM_BASE_URL='your-llm-base-url'")
    print("   export DEFAULT_LLM_MODEL_NAME='your-model-name'")
    print("2. 配置 Gemini CLI Bridge MCP 服务器:")
    print("   cd mcp_servers/gemini-cli-bridge")
    print("   cp .env.example .env")
    print("   # 编辑 .env 文件，设置自定义 API 配置")
    print("3. 安装 Gemini CLI Bridge 依赖:")
    print("   cd mcp_servers/gemini-cli-bridge")
    print("   python -m venv venv")
    print("   source venv/bin/activate  # Windows: venv\\Scripts\\activate")
    print("   pip install -e .")
    print("4. 运行演示:")
    print("   python examples/agents/gemini_cli_bridge_demo.py")
    print("5. 演示将启动 Web 服务，你可以通过浏览器与基于原版 Gemini CLI 的 AI 交互")
    print("")
    print("🚀 基于原版 Google Gemini CLI 的完整功能集")
    print("✨ 支持自定义 API 接口配置")
    print("🔧 无需重新实现，直接使用 Gemini CLI 所有功能")
    print("")
    
    asyncio.run(main())