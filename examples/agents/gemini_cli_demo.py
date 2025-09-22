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


# Gemini CLI 专用系统提示词
GEMINI_SYSTEM_PROMPT = """
你是一个 Gemini CLI 工具专家，具备以下特定能力：
${tools_description}

根据用户的问题选择合适的工具。
如果不需要工具，请直接回应。
如果回答用户问题需要多次工具调用，请一次只调用一个工具。用户收到工具结果后，会为你提供工具调用结果的反馈。

Gemini CLI 工具使用说明：
1. 能力评估：
   - 审查任务需求与你的能力：
     * AI 对话和聊天
     * 代码分析和审查
     * 代码生成和优化
     * 命令行工具执行
   - 如果任务超出能力：
     * 明确识别缺失的能力
     * 返回到 master_agent 并说明原因
     * 建议替代方法

2. 工具使用指南：
   - gemini_chat: 用于一般对话、问答、文本生成
   - gemini_analyze_code: 用于代码分析、审查、性能评估
   - gemini_generate_code: 用于根据描述生成代码
   - gemini_execute_command: 用于执行 Gemini CLI 命令

3. 当你需要使用工具时，必须只用以下确切的 JSON 格式回应：
```json
{
    "think": "你的思考过程（如果需要分析）",
    "tool_name": "工具名称",
    "arguments": {
        "参数名称": "参数值"
    }
}
```

4. 当任务超出能力时：
```json
{
    "status": "capability_mismatch",
    "details": "清楚解释为什么无法完成任务",
    "recommendation": "建议替代方法或智能体"
}
```

5. 代码处理最佳实践：
   - 分析代码时提供具体的改进建议
   - 生成代码时确保代码质量和可读性
   - 包含适当的注释和文档
   - 验证代码语法和逻辑正确性

收到工具响应后：
1. 将原始数据转换为自然的对话回应
2. 答案应简洁但内容丰富
3. 专注于最相关的信息
4. 使用用户问题中的适当上下文
5. 避免简单重复原始数据

请只使用上面明确定义的工具。
"""

# Master 智能体系统提示词
MASTER_SYSTEM_PROMPT = """
你是一个有用的助手，可以使用这些工具：
${tools_description}

根据用户的问题选择合适的工具。
如果不需要工具，请直接回应。
如果回答用户问题需要多次工具调用，请一次只调用一个工具。用户收到工具结果后，会为你提供工具调用结果的反馈。

重要指示：在将任务委托给子智能体时，你必须始终提供明确、详细的操作指示。永远不要假设子智能体在没有明确指导的情况下知道该做什么。

Master 智能体的重要指示：
1. 子智能体任务委托（必需要求）：
   - 始终包含需要执行操作的详细说明
   - 始终指定确切的任务目标和预期结果
   - 始终提供完整的上下文，包括所有相关信息
   - 永远不要在没有明确指示的情况下委托任务
   - 永远不要假设子智能体理解任务而不提供明确指导
   - 分析任务以确定哪个子智能体最合适
   - 将复杂任务分解为清晰的原子操作

2. 当你需要使用工具或委托给子智能体时，用确切的 JSON 格式回应：
```json
{
    "think": "你对任务和委托策略的分析",
    "tool_name": "工具或子智能体名称",
    "arguments": {
        "query": "必需：关于需要执行什么操作以及为什么的详细指示",
        "task_context": {
            "objective": "需要完成的清晰描述",
            "background": "完整的背景信息",
            "constraints": "任何限制或要求",
            "validation_rules": "如何验证成功"
        }
    }
}
```

收到工具或子智能体响应后：
1. 根据预期标准验证响应
2. 将技术结果转换为清晰的自然语言
3. 用新信息更新任务上下文
4. 根据结果确定下一步
5. 保持清晰的进度跟踪

请只使用上面明确定义的工具。
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
        """创建并配置 Gemini CLI 工具组件。"""
        return oxy.StdioMCPClient(
            name="gemini_tools",
            params={
                "command": "python",
                "args": ["mcp_servers/gemini_cli/gemini_cli_server.py"],
                "env": {
                    "GEMINI_API_KEY": get_env_var("GEMINI_API_KEY", expected_type=str, default_val="")
                }
            },
            category="tool",
            class_name="StdioMCPClient",
            desc="Gemini CLI tools for AI operations",
            desc_for_llm="Tools for Gemini AI chat, code analysis, generation and command execution",
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
            desc="A tool for Gemini AI operations like chat, code analysis, code generation and command execution.",
            desc_for_llm="Agent for Gemini AI operations and code assistance",
            category="agent",
            class_name="ReActAgent",
            tools=["gemini_tools"],
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
            desc="Master agent for coordinating Gemini AI operations",
            desc_for_llm="Master agent that coordinates Gemini AI chat, code analysis and generation",
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
                await mas.start_web_service(first_query=query, port=8081)
                logger.info("Gemini CLI service completed successfully")
        except Exception as e:
            logger.error(f"Error running Gemini CLI demo: {str(e)}")
            raise


async def main():
    """Gemini CLI 演示的主入口点。"""
    try:
        # 检查环境变量
        try:
            gemini_key = get_env_var("GEMINI_API_KEY", expected_type=str, default_val="")
            if not gemini_key:
                logger.warning("⚠️  警告: 未设置 GEMINI_API_KEY 环境变量")
                logger.warning("   请运行: export GEMINI_API_KEY='your-api-key'")
                logger.warning("   演示将继续运行，但 Gemini 功能可能受限")
        except Exception:
            logger.warning("⚠️  警告: 无法读取 GEMINI_API_KEY 环境变量")
            logger.warning("   演示将继续运行，但 Gemini 功能可能受限")
        
        demo = GeminiCLIDemo()
        await demo.run_demo()
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise


if __name__ == "__main__":
    print("🎯 Gemini CLI OxyGent 演示")
    print("=" * 50)
    print("📝 使用说明:")
    print("1. 设置必需的环境变量:")
    print("   export DEFAULT_LLM_API_KEY='your-llm-api-key'")
    print("   export DEFAULT_LLM_BASE_URL='your-llm-base-url'")
    print("   export DEFAULT_LLM_MODEL_NAME='your-model-name'")
    print("   export GEMINI_API_KEY='your-gemini-api-key'")
    print("2. 运行演示:")
    print("   python examples/agents/gemini_cli_demo.py")
    print("3. 演示将启动 Web 服务，你可以通过浏览器与 Gemini AI 交互")
    print("")
    
    asyncio.run(main())