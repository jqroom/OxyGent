"""Demo for using OxyGent with Gemini CLI tools."""

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


# Gemini Bridge Python MCP 工具专用系统提示词
GEMINI_SYSTEM_PROMPT = """
你是一个 Gemini Bridge Python MCP 工具专家，负责处理各种任务包括 AI 对话、代码分析、文件操作等。

**🔒 重要：沙盒环境路径说明**
你当前运行在沙盒模式中，所有文件操作都限制在 `cache_dir/gemini_cli_workspace` 目录内：
- **相对路径**：如 `./myfile.txt` 或 `subfolder/data.json` 都相对于沙盒目录 `cache_dir/gemini_cli_workspace`
- **当前目录**：`.` 指向沙盒目录 `cache_dir/gemini_cli_workspace`
- **路径安全**：所有路径会自动验证并限制在沙盒目录内，确保安全性
- **用户路径意图**：当用户提到路径如 `"/path/to/your/local/directory"` 时，这应理解为相对于沙盒目录的路径概念

可用工具：
${tools_description}

**处理策略**：
1. **简单对话/问候**：使用 chat_completion 工具进行 AI 对话
2. **代码分析**：使用 analyze_code 工具
3. **文件操作**：使用 read_file, write_file, list_files 等工具（所有路径相对于沙盒目录）
4. **命令执行**：使用 execute_command 工具（工作目录限制在沙盒内）
5. **网络操作**：使用 web_fetch, web_search 工具
6. **记忆管理**：使用 memory 工具
7. **路径解释**：使用 explain_path 工具解释路径含义和沙盒映射关系

**工具调用格式**：
```json
{
    "think": "分析任务需求和选择工具的原因",
    "tool_name": "具体工具名称",
    "arguments": {
        "参数名": "参数值"
    }
}
```

**重要**：
- 对于用户问候（如"你好"），使用 chat_completion 工具，参数格式：
  ```json
  {
      "tool_name": "chat_completion",
      "arguments": {
          "messages": ["你好！有什么我可以帮你的吗？"]
      }
  }
  ```

- 对于代码分析请求，使用 analyze_code 工具
- 对于文件操作，使用相应的文件工具
- 对于路径理解问题，使用 explain_path 工具，参数格式：
  ```json
  {
      "tool_name": "explain_path",
      "arguments": {
          "path": "需要解释的路径"
      }
  }
  ```
- 如果不需要工具，直接回应

**错误处理**：
如果任务超出能力，回应：
```json
{
    "status": "capability_mismatch", 
    "details": "说明无法完成的原因",
    "recommendation": "建议的替代方案"
}
```

收到工具响应后，将结果转换为自然、有用的回答。
"""

# Master 智能体系统提示词
MASTER_SYSTEM_PROMPT = """
你是一个 Master 智能体，负责协调和管理子智能体来完成用户任务。

可用的子智能体：
- gemini_agent: 专门处理 AI 对话、代码分析、文件操作等任务

对于用户的任何问题或请求，你应该：

1. **简单对话和问答**：直接委托给 gemini_agent 处理
2. **代码分析和文件操作**：委托给 gemini_agent 处理  
3. **复杂任务**：分解后委托给相应的子智能体

**重要**：对于用户的问候、简单问答、代码相关问题，都应该委托给 gemini_agent。

当委托给子智能体时，使用以下 JSON 格式：
```json
{
    "think": "分析用户需求和委托策略",
    "tool_name": "gemini_agent",
    "arguments": {
        "query": "用户的原始问题或请求",
        "task_context": {
            "objective": "明确的任务目标",
            "background": "相关背景信息",
            "constraints": "任何限制条件",
            "validation_rules": "成功标准"
        }
    }
}
```

**示例**：
用户说"你好"时，应该回应：
```json
{
    "think": "用户在问候，这是简单的对话请求，应该委托给gemini_agent处理",
    "tool_name": "gemini_agent", 
    "arguments": {
        "query": "你好！有什么我可以帮你的吗？",
        "task_context": {
            "objective": "友好地回应用户问候并询问如何帮助",
            "background": "这是对话的开始",
            "constraints": "保持友好和专业",
            "validation_rules": "提供有用的回应"
        }
    }
}
```

请始终委托给合适的子智能体，不要尝试直接回答。
"""


class GeminiCLIDemo:
    """Gemini CLI 演示实现类。"""

    def __init__(self):
        """使用配置初始化 Gemini CLI 演示。"""
        try:
            self.config = load_config()
            Config.set_agent_llm_model("default_llm")
            self.oxy_space = self._create_oxy_space()
        except Exception as e:
            logger.error(f"Failed to initialize GeminiCLIDemo: {str(e)}")
            raise

    def _create_oxy_space(self) -> list:
        """创建并配置包含所有必需组件的 oxy 空间。"""
        try:
            return [
                self._create_http_llm(),
                self._create_gemini_tools(),
                self._create_gemini_agent(),
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

    def _create_gemini_tools(self) -> oxy.StdioMCPClient:
        """创建并配置 Gemini Bridge Python MCP 工具组件。"""
        return oxy.StdioMCPClient(
            name="gemini_bridge_tools",
            params={
                "command": "/bin/bash",
                "args": ["-c", "cd mcp_servers/gemini-cli-custom-bridge-python && PYTHONPATH=src python -m gemini_bridge"],
                "cwd": ".",
                "env": {
                    # 使用京东云 AI 配置，不需要 GEMINI_API_KEY
                    "PATH": os.environ.get("PATH", ""),
                    # 沙盒路径上下文环境变量
                    "GEMINI_SANDBOX_DIR": "cache_dir/gemini_cli_workspace",
                    "GEMINI_PROJECT_ROOT": ".",
                    "GEMINI_PATH_CONTEXT": "sandbox_mode"
                }
            },
            category="tool",
            class_name="StdioMCPClient",
            desc="Gemini Bridge Python MCP tools for AI operations",
            desc_for_llm="Tools for AI chat completion, code analysis, file operations, command execution, web search and memory management",
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=30,
            retries=3,
            delay=1,
            friendly_error_text="Gemini CLI operation failed",
            semaphore=2,
        )

    def _create_gemini_agent(self) -> oxy.ReActAgent:
        """创建并配置 Gemini 智能体组件。"""
        return oxy.ReActAgent(
            name="gemini_agent",
            desc="A tool for AI operations including chat, code analysis, file operations, command execution, web search and memory management.",
            desc_for_llm="Agent for comprehensive AI operations and development assistance using Gemini Bridge Python MCP tools",
            category="agent",
            class_name="ReActAgent",
            tools=["gemini_bridge_tools"],
            llm_model="default_llm",
            prompt=GEMINI_SYSTEM_PROMPT,
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
        """创建并配置主智能体组件。"""
        return oxy.ReActAgent(
            name="master_agent",
            desc="Master agent for coordinating AI operations via Gemini Bridge Python MCP tools",
            desc_for_llm="Master agent that coordinates comprehensive AI operations including chat, code analysis, file operations, and web search",
            category="agent",
            class_name="ReActAgent",
            sub_agents=["gemini_agent"],
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
        query: str = "你好！请简单介绍一下你自己，然后帮我分析这段Python代码的性能问题：\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
    ):
        """使用指定查询运行 Gemini CLI 演示。"""
        try:
            async with MAS(oxy_space=self.oxy_space) as mas:
                logger.info(f"Starting Gemini CLI service with query: {query}")
                await mas.start_web_service(first_query=query, port=8080)
                logger.info("Gemini CLI service completed successfully")
        except Exception as e:
            logger.error(f"Error running Gemini CLI demo: {str(e)}")
            raise


async def main():
    """Gemini CLI 演示的主入口点。"""
    try:
        # 检查环境变量 - 京东云 AI 配置
        try:
            # 检查必需的京东云 AI 环境变量
            required_vars = [
                "NEXT_PUBLIC_AI_API_URL",
                "NEXT_PUBLIC_AI_MODEL", 
                "NEXT_PUBLIC_AI_API_KEY"
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
                logger.warning("⚠️  警告: 未设置以下京东云 AI 环境变量:")
                for var in missing_vars:
                    logger.warning(f"   {var}")
                logger.warning("   请确保在 mcp_servers/gemini-cli-custom-bridge-python/.env 中配置这些变量")
                logger.warning("   演示将继续运行，但 AI 功能可能受限")
        except Exception as e:
            logger.warning(f"⚠️  警告: 检查环境变量时出错: {str(e)}")
            logger.warning("   演示将继续运行，但功能可能受限")
        
        demo = GeminiCLIDemo()
        await demo.run_demo()
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise


if __name__ == "__main__":
    print("🎯 Gemini Bridge Python MCP OxyGent 演示")
    print("=" * 50)
    print("📝 使用说明:")
    print("1. 设置必需的环境变量:")
    print("   export DEFAULT_LLM_API_KEY='your-llm-api-key'")
    print("   export DEFAULT_LLM_BASE_URL='your-llm-base-url'")
    print("   export DEFAULT_LLM_MODEL_NAME='your-model-name'")
    print("2. 配置 Gemini Bridge Python MCP 服务器:")
    print("   cd mcp_servers/gemini-cli-custom-bridge-python")
    print("   cp .env.example .env")
    print("   # 编辑 .env 文件，设置京东云 AI 配置")
    print("3. 安装 Python MCP 服务器依赖:")
    print("   ./install.sh")
    print("4. 运行演示:")
    print("   python examples/agents/gemini_cli_demo.py")
    print("5. 演示将启动 Web 服务，你可以通过浏览器与 AI 交互")
    print("")
    
    asyncio.run(main())