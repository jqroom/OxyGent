#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequest,
    CallToolRequestSchema,
    CallToolResult,
    ErrorCode,
    ListToolsRequestSchema,
    McpError,
} from "@modelcontextprotocol/sdk/types.js";
import { exec } from "child_process";
import { config } from "dotenv";
import fs from "fs/promises";
import fetch, { Response } from "node-fetch";
import path from "path";
import { fileURLToPath } from "url";
import { promisify } from "util";
import {
    handleEditTool as handleEdit,
    handleGlobTool as handleGlob,
    handleGrepTool as handleGrep,
    handleMemoryTool as handleMemory,
    handleWebFetchTool as handleWebFetch,
    handleWebSearchTool as handleWebSearch,
} from "./gemini-tools.js";
import {
    PATH_CONFIG,
    resolveSafePath,
    resolveSafeWorkingDirectory,
} from "./path-manager.js";
import { ChatCompletionArgs, CodeAnalysisArgs } from "./types.js";

const execAsync = promisify(exec);

// 获取当前文件的目录路径（ES 模块中 __dirname 的替代方案）
const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 注意：路径验证功能已迁移到 path-manager.js 模块中统一管理
// 这里保留注释以便理解代码结构的变化

// 加载环境变量 - 优先加载项目根目录的 .env.local
config({ path: path.resolve(__dirname, "../../.env.local") });
// 然后加载当前目录的 .env 作为备用
config();

// 服务器信息
const server = new Server(
  {
    name: "custom-ai-bridge",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Custom AI 配置 - 从项目根目录的 .env.local 读取
const NEXT_PUBLIC_AI_API_URL =
  process.env.NEXT_PUBLIC_AI_API_URL ||
  process.env.NEXT_PUBLIC_AI_API_URL ||
  "http://ai-api.custom.com/v1";
const NEXT_PUBLIC_AI_MODEL =
  process.env.NEXT_PUBLIC_AI_MODEL ||
  process.env.NEXT_PUBLIC_AI_MODEL ||
  "Claude-sonnet-4";
const API_KEY = process.env.NEXT_PUBLIC_AI_API_KEY;

// 工具定义
const TOOLS = [
  {
    name: "chat_completion",
    description: "Send a chat completion request to Custom AI",
    inputSchema: {
      type: "object",
      properties: {
        messages: {
          type: "array",
          description: "Array of chat messages",
          items: {
            type: "object",
            properties: {
              role: {
                type: "string",
                enum: ["system", "user", "assistant"],
                description: "Message role",
              },
              content: {
                type: "string",
                description: "Message content",
              },
            },
            required: ["role", "content"],
          },
        },
        model: {
          type: "string",
          description: "Model to use for completion",
          default: NEXT_PUBLIC_AI_MODEL,
        },
        temperature: {
          type: "number",
          description: "Temperature for response generation",
          minimum: 0,
          maximum: 2,
          default: 0.7,
        },
        max_tokens: {
          type: "number",
          description: "Maximum tokens in response",
          minimum: 1,
          default: 2000,
        },
        stream: {
          type: "boolean",
          description: "Whether to stream the response",
          default: false,
        },
      },
      required: ["messages"],
    },
  },
  {
    name: "analyze_code",
    description: "Analyze code using Custom AI",
    inputSchema: {
      type: "object",
      properties: {
        code: {
          type: "string",
          description: "Code to analyze",
        },
        language: {
          type: "string",
          description: "Programming language of the code",
        },
        analysis_type: {
          type: "string",
          description: "Type of analysis to perform",
          enum: ["review", "optimize", "explain", "debug"],
          default: "review",
        },
      },
      required: ["code"],
    },
  },
  {
    name: "read_file",
    description: "Read the contents of a file",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Path to the file to read",
        },
      },
      required: ["path"],
    },
  },
  {
    name: "write_file",
    description: "Write content to a file",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Path to the file to write",
        },
        content: {
          type: "string",
          description: "Content to write to the file",
        },
      },
      required: ["path", "content"],
    },
  },
  {
    name: "list_files",
    description: "List files in a directory",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Path to the directory to list",
          default: ".",
        },
      },
    },
  },
  {
    name: "execute_command",
    description: "Execute a shell command",
    inputSchema: {
      type: "object",
      properties: {
        command: {
          type: "string",
          description: "Command to execute",
        },
        cwd: {
          type: "string",
          description: "Working directory for the command",
          default: ".",
        },
      },
      required: ["command"],
    },
  },
  {
    name: "read_many_files",
    description: "Read multiple files at once and return their contents",
    inputSchema: {
      type: "object",
      properties: {
        paths: {
          type: "array",
          description: "Array of file paths to read",
          items: {
            type: "string",
          },
        },
        include_path_in_response: {
          type: "boolean",
          description: "Whether to include file path in the response",
          default: true,
        },
      },
      required: ["paths"],
    },
  },
  {
    name: "grep",
    description: "Search for patterns in files using grep-like functionality",
    inputSchema: {
      type: "object",
      properties: {
        pattern: {
          type: "string",
          description: "Pattern to search for",
        },
        path: {
          type: "string",
          description: "File or directory path to search in",
          default: ".",
        },
        recursive: {
          type: "boolean",
          description: "Search recursively in directories",
          default: true,
        },
        case_sensitive: {
          type: "boolean",
          description: "Case sensitive search",
          default: false,
        },
        line_numbers: {
          type: "boolean",
          description: "Show line numbers in results",
          default: true,
        },
      },
      required: ["pattern"],
    },
  },
  {
    name: "glob",
    description: "Find files matching glob patterns",
    inputSchema: {
      type: "object",
      properties: {
        pattern: {
          type: "string",
          description: "Glob pattern to match files",
        },
        cwd: {
          type: "string",
          description: "Working directory for glob search",
          default: ".",
        },
      },
      required: ["pattern"],
    },
  },
  {
    name: "edit",
    description: "Edit files with various operations (replace, insert, delete)",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Path to the file to edit",
        },
        operation: {
          type: "string",
          description: "Edit operation to perform",
          enum: ["replace", "insert", "delete"],
        },
        old_text: {
          type: "string",
          description: "Text to replace (for replace operation)",
        },
        new_text: {
          type: "string",
          description: "New text to insert or replace with",
        },
        line_number: {
          type: "number",
          description: "Line number for insert/delete operations",
        },
        start_line: {
          type: "number",
          description: "Start line for delete operation",
        },
        end_line: {
          type: "number",
          description: "End line for delete operation",
        },
      },
      required: ["path", "operation"],
    },
  },
  {
    name: "web_fetch",
    description: "Fetch content from web URLs",
    inputSchema: {
      type: "object",
      properties: {
        url: {
          type: "string",
          description: "URL to fetch content from",
        },
        method: {
          type: "string",
          description: "HTTP method to use",
          enum: ["GET", "POST", "PUT", "DELETE"],
          default: "GET",
        },
        headers: {
          type: "object",
          description: "HTTP headers to send",
        },
        body: {
          type: "string",
          description: "Request body for POST/PUT requests",
        },
      },
      required: ["url"],
    },
  },
  {
    name: "web_search",
    description: "Search the web using DuckDuckGo",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "Search query",
        },
        num_results: {
          type: "number",
          description: "Number of results to return",
          default: 5,
          minimum: 1,
          maximum: 20,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "memory",
    description: "Store and retrieve information in memory",
    inputSchema: {
      type: "object",
      properties: {
        action: {
          type: "string",
          description: "Memory action to perform",
          enum: ["store", "retrieve", "list", "clear"],
        },
        key: {
          type: "string",
          description: "Memory key for store/retrieve operations",
        },
        value: {
          type: "string",
          description: "Value to store (for store action)",
        },
      },
      required: ["action"],
    },
  },
];

// 列出可用工具
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS,
  };
});

// 处理工具调用
server.setRequestHandler(
  CallToolRequestSchema,
  async (request: CallToolRequest): Promise<CallToolResult> => {
    const { name, arguments: args } = request.params;

    try {
      switch (name) {
        case "chat_completion":
          // 验证参数类型
          if (!args || typeof args !== "object" || !("messages" in args)) {
            throw new Error(
              "Invalid arguments for chat_completion: missing messages"
            );
          }
          return await handleChatCompletion(
            args as unknown as ChatCompletionArgs
          );
        case "analyze_code":
          // 验证参数类型
          if (!args || typeof args !== "object" || !("code" in args)) {
            throw new Error("Invalid arguments for analyze_code: missing code");
          }
          return await handleCodeAnalysis(args as unknown as CodeAnalysisArgs);
        case "read_file":
          if (!args || typeof args !== "object" || !("path" in args)) {
            throw new Error("Invalid arguments for read_file: missing path");
          }
          return await handleReadFile(args as { path: string });
        case "write_file":
          if (
            !args ||
            typeof args !== "object" ||
            !("path" in args) ||
            !("content" in args)
          ) {
            throw new Error(
              "Invalid arguments for write_file: missing path or content"
            );
          }
          return await handleWriteFile(
            args as { path: string; content: string }
          );
        case "list_files":
          return await handleListFiles(args as { path?: string });
        case "read_many_files":
          if (!args || typeof args !== "object" || !("paths" in args)) {
            throw new Error(
              "Invalid arguments for read_many_files: missing paths"
            );
          }
          return await handleReadManyFiles(
            args as { paths: string[]; include_path_in_response?: boolean }
          );
        case "execute_command":
          if (!args || typeof args !== "object" || !("command" in args)) {
            throw new Error(
              "Invalid arguments for execute_command: missing command"
            );
          }
          return await handleExecuteCommand(
            args as { command: string; cwd?: string }
          );
        case "grep":
          if (!args || typeof args !== "object" || !("pattern" in args)) {
            throw new Error("Invalid arguments for grep: missing pattern");
          }
          return await handleGrep(
            args as {
              pattern: string;
              path?: string;
              recursive?: boolean;
              case_insensitive?: boolean;
              line_numbers?: boolean;
            }
          );
        case "glob":
          if (!args || typeof args !== "object" || !("pattern" in args)) {
            throw new Error("Invalid arguments for glob: missing pattern");
          }
          return await handleGlob(args as { pattern: string; cwd?: string });
        case "edit":
          if (
            !args ||
            typeof args !== "object" ||
            !("path" in args) ||
            !("operation" in args)
          ) {
            throw new Error(
              "Invalid arguments for edit: missing path or operation"
            );
          }
          return await handleEdit(
            args as {
              path: string;
              operation: "replace" | "insert" | "delete";
              old_text?: string;
              new_text?: string;
              line_number?: number;
              content?: string;
            }
          );
        case "web_fetch":
          if (!args || typeof args !== "object" || !("url" in args)) {
            throw new Error("Invalid arguments for web_fetch: missing url");
          }
          return await handleWebFetch(
            args as {
              url: string;
              method?: "GET" | "POST" | "PUT" | "DELETE";
              headers?: Record<string, string>;
              body?: string;
            }
          );
        case "web_search":
          if (!args || typeof args !== "object" || !("query" in args)) {
            throw new Error("Invalid arguments for web_search: missing query");
          }
          return await handleWebSearch(
            args as { query: string; num_results?: number }
          );
        case "memory":
          if (!args || typeof args !== "object" || !("operation" in args)) {
            throw new Error("Invalid arguments for memory: missing operation");
          }
          return await handleMemory(
            args as {
              operation: "get" | "set" | "delete" | "list";
              key?: string;
              value?: string;
            }
          );
        default:
          throw new McpError(ErrorCode.MethodNotFound, `Unknown tool: ${name}`);
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      throw new McpError(
        ErrorCode.InternalError,
        `Tool execution failed: ${errorMessage}`
      );
    }
  }
);

// 处理聊天完成请求
async function handleChatCompletion(
  args: ChatCompletionArgs
): Promise<CallToolResult> {
  const {
    messages,
    model = NEXT_PUBLIC_AI_MODEL,
    temperature = 0.7,
    max_tokens = 2000,
    stream = false,
  } = args;

  // 增强的系统提示词 - 让AI主动调用文件操作工具
  const enhancedSystemPrompt = `你是一个智能的任务执行专家，能够通过 custom-ai-bridge MCP 服务器访问京东云 AI 功能和文件操作功能。

# 核心能力
你拥有以下工具，应该主动使用这些工具来获取完成任务所需的信息：
1. chat_completion - 进行AI对话和推理
2. analyze_code - 分析代码结构、质量和逻辑
3. read_file - 读取文件内容
4. write_file - 写入文件内容
5. list_files - 列出目录文件
6. execute_command - 执行系统命令
7. read_many_files - 批量读取多个文件内容
8. grep - 在文件中搜索模式匹配的内容
9. glob - 查找匹配glob模式的文件
10. edit - 编辑文件（替换、插入、删除操作）
11. web_fetch - 从网络URL获取内容
12. web_search - 使用DuckDuckGo搜索网络内容
13. memory - 存储和检索内存信息

# 工作原则
- **主动探索**: 收到任务后，主动使用 list_files 工具探索项目结构
- **深入了解**: 使用 read_file 工具读取关键文件内容，理解项目架构和代码逻辑
- **智能分析**: 使用 analyze_code 工具分析代码质量和可能的改进点
- **执行验证**: 使用 execute_command 工具执行必要的命令进行验证
- **完整实现**: 使用 write_file 工具完成代码修改和文件创建

# 任务执行流程
1. 接收任务需求后，首先使用 list_files 获取项目目录结构
2. 根据任务类型，使用 read_file 读取相关文件了解现状
3. 如需代码分析，使用 analyze_code 工具进行深入分析
4. 制定详细的实施计划
5. 使用相应工具执行任务（write_file, execute_command等）
6. 验证结果并提供完整的任务总结

# 注意事项
- 始终主动获取必要信息，不要等待用户提供
- 优先使用工具而非询问用户
- 确保对项目结构有充分了解后再进行修改
- 所有操作都要考虑项目的整体架构和最佳实践

现在你可以开始接收和执行各种开发任务，记住要主动使用这些工具来自动完成代码修改、文件操作和系统管理任务。`;

  // 检查是否已有系统消息，如果没有则添加增强的系统提示词
  const enhancedMessages = [...messages];
  const hasSystemMessage = messages.some((msg) => msg.role === "system");

  if (!hasSystemMessage) {
    enhancedMessages.unshift({
      role: "system",
      content: enhancedSystemPrompt,
    });
  } else {
    // 如果已有系统消息，则增强第一个系统消息
    const systemMessageIndex = messages.findIndex(
      (msg) => msg.role === "system"
    );
    if (systemMessageIndex >= 0) {
      enhancedMessages[systemMessageIndex] = {
        ...messages[systemMessageIndex],
        content:
          enhancedSystemPrompt + "\n\n" + messages[systemMessageIndex].content,
      };
    }
  }

  // 构造标准的 OpenAI 格式请求体
  const requestBody = {
    model,
    messages: enhancedMessages,
    temperature,
    max_tokens,
    stream,
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_KEY}`,
  };

  // 修正API路径 - 直接调用 Custom AI API
  const response = await fetch(`${NEXT_PUBLIC_AI_API_URL}/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Chat API error: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  // 处理流式响应
  if (stream) {
    return await handleStreamResponse(response);
  }

  // 处理非流式响应
  return await handleNonStreamResponse(response);
}

// 处理流式响应 - 修复版本，支持真正的流式输出
async function handleStreamResponse(
  response: Response
): Promise<CallToolResult> {
  if (!response.body) {
    throw new Error("No response body for streaming");
  }

  return new Promise((resolve, reject) => {
    let buffer = "";
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    let fullContent = ""; // 用于累积内容并实时输出流式数据
    const chunks: string[] = [];

    // 使用 node-fetch 的事件监听方式处理流式数据
    response.body!.on("data", (chunk: Buffer) => {
      try {
        // 解码数据块
        buffer += chunk.toString("utf8");

        // 按行分割处理SSE数据
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // 保留最后一个可能不完整的行

        for (const line of lines) {
          const trimmedLine = line.trim();

          // 处理SSE数据行
          if (trimmedLine.startsWith("data: ")) {
            const dataContent = trimmedLine.substring(6).trim();

            // 检查是否为结束标记
            if (dataContent === "[DONE]") {
              // 流式响应结束，不返回完整内容，避免重复
              resolve({
                content: [
                  {
                    type: "text" as const,
                    text: "", // 在stream模式中，不返回完整内容
                  },
                ],
                _meta: {
                  streaming: true,
                  chunks_count: chunks.length,
                  final: true,
                  stream_completed: true,
                },
              } as CallToolResult);
              return;
            }

            try {
              const chunkData = JSON.parse(dataContent);

              // 提取流式数据内容
              if (
                chunkData.choices &&
                chunkData.choices[0] &&
                chunkData.choices[0].delta
              ) {
                const delta = chunkData.choices[0].delta;

                if (delta.content) {
                  let content = delta.content;

                  // 处理数组格式的content
                  if (Array.isArray(content)) {
                    content = content.join("");
                  }

                  fullContent += content;
                  chunks.push(content);

                  // 实时输出每个数据块到标准输出，供上层流式处理
                  if (content.trim()) {
                    // 输出 SSE 格式的数据块
                    console.log(
                      `data: ${JSON.stringify({
                        type: "chunk",
                        content: content,
                        done: false,
                        chunk_index: chunks.length - 1,
                      })}`
                    );
                    console.log(""); // SSE 需要空行分隔
                  }
                }
              }
            } catch {
              // 忽略解析错误，继续处理下一行
              console.warn("Failed to parse SSE chunk:", dataContent);
            }
          }
        }
      } catch (error) {
        reject(error);
      }
    });

    response.body!.on("end", () => {
      // 输出流结束标记，但不包含完整内容，避免重复
      console.log(
        `data: ${JSON.stringify({
          type: "done",
          done: true,
          chunks_count: chunks.length,
        })}`
      );
      console.log("");

      // 流结束时只返回元数据，不返回完整内容
      resolve({
        content: [
          {
            type: "text" as const,
            text: "", // 在stream模式中，不返回完整内容
          },
        ],
        _meta: {
          streaming: true,
          chunks_count: chunks.length,
          final: true,
          stream_completed: true,
        },
      } as CallToolResult);
    });

    response.body!.on("error", (error: Error) => {
      console.error(
        `data: ${JSON.stringify({
          type: "error",
          error: error.message,
          done: true,
        })}`
      );
      console.log("");
      reject(error);
    });
  });
}

// 处理非流式响应
async function handleNonStreamResponse(response: Response) {
  const responseText = await response.text();
  let result;

  try {
    // 首先尝试直接解析JSON
    result = JSON.parse(responseText);

    // 处理Custom AI特殊的响应格式
    if (
      result &&
      result.choices &&
      result.choices[0] &&
      result.choices[0].message
    ) {
      const message = result.choices[0].message;

      // 如果content是数组，转换为字符串
      if (Array.isArray(message.content)) {
        message.content = message.content.join("");
      }

      // 对于非流式请求，返回标准格式
      return {
        content: [
          {
            type: "text" as const,
            text: message.content,
          },
        ],
      };
    }
  } catch (parseError) {
    // 如果直接解析失败，检查是否为SSE格式
    const lines = responseText.split("\n");
    let jsonData = null;

    for (const line of lines) {
      const trimmedLine = line.trim();
      if (trimmedLine.startsWith("data: ")) {
        const dataContent = trimmedLine.substring(6).trim();
        if (dataContent.startsWith("{") && dataContent.endsWith("}")) {
          try {
            jsonData = JSON.parse(dataContent);
            break;
          } catch {
            // 继续尝试下一行
            continue;
          }
        }
      }
    }

    if (jsonData) {
      result = jsonData;
    } else {
      // 如果都无法解析，返回原始文本
      result = {
        error: "Unable to parse response",
        raw_response: responseText,
        parse_error:
          parseError instanceof Error ? parseError.message : String(parseError),
      };
    }
  }

  // 默认返回完整的JSON响应
  return {
    content: [
      {
        type: "text" as const,
        text: JSON.stringify(result, null, 2),
      },
    ],
  };
}

// 处理代码分析请求
async function handleCodeAnalysis(
  args: CodeAnalysisArgs
): Promise<CallToolResult> {
  const { code, language, analysis_type = "review" } = args;

  // 构造分析提示
  const analysisPrompts = {
    review: `请对以下${
      language || ""
    }代码进行代码审查，指出潜在问题和改进建议：`,
    optimize: `请优化以下${language || ""}代码，提供性能和可读性改进建议：`,
    explain: `请详细解释以下${language || ""}代码的功能和实现逻辑：`,
    debug: `请帮助调试以下${language || ""}代码，找出可能的错误和问题：`,
  };

  const prompt =
    analysisPrompts[analysis_type as keyof typeof analysisPrompts] ||
    analysisPrompts.review;

  // 构造标准的 OpenAI 格式消息
  const messages = [
    {
      role: "system" as const,
      content: "你是一个专业的代码分析助手，请提供详细、准确的代码分析。",
    },
    {
      role: "user" as const,
      content: `${prompt}\n\n\`\`\`${language || ""}\n${code}\n\`\`\``,
    },
  ];

  // 构造标准的 OpenAI 格式请求体
  const requestBody = {
    model: NEXT_PUBLIC_AI_MODEL,
    messages,
    temperature: 0.3,
    max_tokens: 20000,
    stream: false,
  };

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${API_KEY}`,
  };

  // 直接调用京东云AI的chat/completions接口
  const response = await fetch(`${NEXT_PUBLIC_AI_API_URL}/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Code Analysis API error: ${response.status} ${response.statusText} - ${errorText}`
    );
  }

  // 处理非流式响应
  return await handleNonStreamResponse(response);
}

// 处理文件读取
async function handleReadFile(args: { path: string }) {
  try {
    // 使用统一的路径管理模块验证路径安全性
    const safePath = resolveSafePath(args.path);
    const content = await fs.readFile(safePath, "utf-8");
    return {
      content: [
        {
          type: "text" as const,
          text: content,
        },
      ],
    };
  } catch (error) {
    // 返回错误响应而不是抛出异常
    return {
      content: [
        {
          type: "text" as const,
          text: `Access denied: Failed to read file ${args.path}: ${error}`,
        },
      ],
      isError: true,
    };
  }
}

// 处理批量文件读取
async function handleReadManyFiles(args: {
  paths: string[];
  include_path_in_response?: boolean;
}): Promise<CallToolResult> {
  const { paths, include_path_in_response = true } = args;

  if (!Array.isArray(paths) || paths.length === 0) {
    return {
      content: [
        {
          type: "text" as const,
          text: "Error: paths must be a non-empty array",
        },
      ],
      isError: true,
    };
  }

  const results: Array<{
    path: string;
    content?: string;
    error?: string;
  }> = [];

  // 并行读取所有文件
  const readPromises = paths.map(async (filePath) => {
    try {
      // 使用统一的路径管理模块验证路径安全性
      const safePath = resolveSafePath(filePath);
      const content = await fs.readFile(safePath, "utf-8");
      return {
        path: filePath,
        content,
      };
    } catch (error) {
      return {
        path: filePath,
        error: `Failed to read file: ${error}`,
      };
    }
  });

  const fileResults = await Promise.all(readPromises);
  results.push(...fileResults);

  // 格式化输出
  let responseText = "";

  if (include_path_in_response) {
    // 包含文件路径的格式
    for (const result of results) {
      responseText += `=== ${result.path} ===\n`;
      if (result.error) {
        responseText += `ERROR: ${result.error}\n`;
      } else {
        responseText += `${result.content}\n`;
      }
      responseText += "\n";
    }
  } else {
    // 仅包含文件内容的格式
    for (const result of results) {
      if (result.error) {
        responseText += `ERROR reading ${result.path}: ${result.error}\n`;
      } else {
        responseText += `${result.content}\n`;
      }
    }
  }

  // 检查是否有任何错误
  const hasErrors = results.some((result) => result.error);

  return {
    content: [
      {
        type: "text" as const,
        text: responseText.trim(),
      },
    ],
    isError: hasErrors,
    _meta: {
      files_read: results.length,
      successful_reads: results.filter((r) => !r.error).length,
      failed_reads: results.filter((r) => r.error).length,
    },
  };
}

// 处理文件写入
async function handleWriteFile(args: { path: string; content: string }) {
  try {
    console.error(`[DEBUG] handleWriteFile called with path: ${args.path}`);

    // 使用统一的路径管理模块验证路径安全性
    const safePath = resolveSafePath(args.path);
    console.error(`[DEBUG] Validated path: ${safePath}`);

    // 检查路径意图：判断是否为有效的文件路径
    const fileName = path.basename(safePath);
    const endsWithSlash = args.path.endsWith("/") || args.path.endsWith("\\");

    // 如果路径以斜杠结尾，明确表示这是一个目录路径，不应该写入文件
    if (endsWithSlash) {
      throw new Error(
        `Path ${args.path} ends with slash, indicating a directory. Cannot write file to directory path.`
      );
    }

    // 定义合法的文件扩展名白名单
    const validExtensions = [
      // 代码文件
      ".js",
      ".ts",
      ".jsx",
      ".tsx",
      ".py",
      ".java",
      ".c",
      ".cpp",
      ".h",
      ".hpp",
      ".cs",
      ".php",
      ".rb",
      ".go",
      ".rs",
      ".swift",
      ".kt",
      ".scala",
      ".clj",
      ".hs",
      ".ml",
      ".fs",
      ".vb",
      ".pl",
      ".sh",
      ".bat",
      ".ps1",
      // 标记语言
      ".html",
      ".htm",
      ".xml",
      ".svg",
      ".md",
      ".markdown",
      ".rst",
      ".tex",
      // 样式文件
      ".css",
      ".scss",
      ".sass",
      ".less",
      ".styl",
      // 配置文件
      ".json",
      ".yaml",
      ".yml",
      ".toml",
      ".ini",
      ".cfg",
      ".conf",
      ".config",
      // 数据文件
      ".csv",
      ".tsv",
      ".sql",
      ".db",
      ".sqlite",
      ".xml",
      // 文档文件
      ".txt",
      ".log",
      ".readme",
      ".license",
      ".changelog",
      // 模板文件
      ".ejs",
      ".hbs",
      ".mustache",
      ".twig",
      ".jinja",
      ".liquid",
      // 其他常见文件
      ".gitignore",
      ".gitattributes",
      ".editorconfig",
      ".prettierrc",
      ".eslintrc",
      ".babelrc",
      ".npmrc",
      ".nvmrc",
      ".dockerignore",
      ".htaccess",
    ];

    // 定义合法的隐藏文件名（以点开头且无扩展名）
    const validHiddenFiles = [
      ".env",
      ".gitignore",
      ".gitattributes",
      ".editorconfig",
      ".prettierrc",
      ".eslintrc",
      ".babelrc",
      ".npmrc",
      ".nvmrc",
      ".dockerignore",
      ".htaccess",
      ".bashrc",
      ".zshrc",
      ".vimrc",
      ".tmux",
      ".profile",
      ".bashprofile",
    ];

    // 检查文件是否有合法的扩展名或是合法的隐藏文件
    let isValidFile = false;

    if (fileName.startsWith(".") && !fileName.includes(".", 1)) {
      // 隐藏文件（以点开头且无扩展名）
      isValidFile = validHiddenFiles.includes(fileName);
    } else {
      // 普通文件，检查扩展名
      const extension = path.extname(fileName).toLowerCase();
      isValidFile = extension !== "" && validExtensions.includes(extension);
    }

    if (!isValidFile) {
      const extension = path.extname(fileName);
      throw new Error(
        `Path ${
          args.path
        } is not a valid file path. File must have a recognized file extension or be a valid hidden file. Current file: "${fileName}" (${
          extension ? `extension: ${extension}` : "no extension"
        }). Supported extensions: ${validExtensions
          .slice(0, 10)
          .join(", ")}... and valid hidden files: ${validHiddenFiles
          .slice(0, 5)
          .join(", ")}...`
      );
    }

    console.error(`[DEBUG] Valid file path detected: ${fileName}`);

    // 检查路径是否存在
    try {
      const stats = await fs.stat(safePath);
      if (stats.isDirectory()) {
        // 如果路径是一个目录，抛出错误
        throw new Error(`Path ${args.path} is a directory, cannot write file`);
      }
      console.error(`[DEBUG] File already exists, will overwrite: ${safePath}`);
    } catch (statError: unknown) {
      if ((statError as NodeJS.ErrnoException).code === "ENOENT") {
        // 文件不存在，这是正常情况，继续创建
        console.error(`[DEBUG] File does not exist, will create: ${safePath}`);
      } else {
        // 其他错误，重新抛出
        throw statError;
      }
    }

    // 只有在确认是文件路径的情况下，才创建父目录
    const dir = path.dirname(safePath);

    // 检查父目录是否存在
    try {
      const dirStats = await fs.stat(dir);
      if (!dirStats.isDirectory()) {
        throw new Error(`Parent path ${dir} exists but is not a directory`);
      }
      console.error(`[DEBUG] Parent directory already exists: ${dir}`);
    } catch (dirError: unknown) {
      if ((dirError as NodeJS.ErrnoException).code === "ENOENT") {
        // 父目录不存在，创建它（只创建文件的父目录，不是文件本身的目录）
        console.error(`[DEBUG] Creating parent directory: ${dir}`);
        await fs.mkdir(dir, { recursive: true });
      } else {
        // 其他错误，重新抛出
        throw dirError;
      }
    }

    // 写入文件内容
    console.error(`[DEBUG] Writing content to file: ${safePath}`);
    await fs.writeFile(safePath, args.content, "utf-8");

    console.error(`[DEBUG] File write successful: ${safePath}`);
    return {
      content: [
        {
          type: "text" as const,
          text: `Successfully wrote to ${args.path}`,
        },
      ],
    };
  } catch (error) {
    console.error(`[ERROR] handleWriteFile failed:`, error);
    // 返回错误响应而不是抛出异常
    return {
      content: [
        {
          type: "text" as const,
          text: `Access denied: Failed to write file ${args.path}: ${error}`,
        },
      ],
      isError: true,
    };
  }
}

// 处理文件列表
async function handleListFiles(args: { path?: string }) {
  try {
    console.error(
      `[DEBUG] handleListFiles called with path: ${args.path || "undefined"}`
    );

    // 修复默认路径处理：如果没有提供路径，默认列出temp目录内容
    // 使用 "." 表示当前工作目录（即temp目录）
    const inputPath = args.path || ".";
    console.error(`[DEBUG] Using input path: ${inputPath}`);

    const safePath = resolveSafePath(inputPath);
    console.error(`[DEBUG] Validated path: ${safePath}`);

    console.error(`[DEBUG] Reading directory: ${safePath}`);
    const files = await fs.readdir(safePath, { withFileTypes: true });

    const fileList = files.map((file) => ({
      name: file.name,
      type: file.isDirectory() ? "directory" : "file",
    }));

    console.error(`[DEBUG] Found ${fileList.length} files/directories`);
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(fileList, null, 2),
        },
      ],
    };
  } catch (error) {
    console.error(`[ERROR] handleListFiles failed:`, error);
    // 返回错误响应而不是抛出异常
    return {
      content: [
        {
          type: "text" as const,
          text: `Access denied: Failed to list files in ${
            args.path || "temp directory"
          }: ${error}`,
        },
      ],
      isError: true,
    };
  }
}

// 处理命令执行
async function handleExecuteCommand(args: { command: string; cwd?: string }) {
  try {
    // 使用统一的路径管理模块验证工作目录安全性，默认使用 autodev 根目录下的 temp
    const defaultTempPath = args.cwd || PATH_CONFIG.TEMP_DIR;
    const safeWorkDir = resolveSafeWorkingDirectory(defaultTempPath);

    // 确保工作目录存在
    await fs.mkdir(safeWorkDir, { recursive: true });

    const { stdout, stderr } = await execAsync(args.command, {
      cwd: safeWorkDir,
      timeout: 30000, // 30秒超时
    });

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              stdout: stdout.trim(),
              stderr: stderr.trim(),
              success: true,
              workingDirectory: safeWorkDir,
            },
            null,
            2
          ),
        },
      ],
    };
  } catch (error: unknown) {
    const execError = error as {
      stdout?: string;
      stderr?: string;
      message?: string;
      code?: number;
    };
    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(
            {
              stdout: execError.stdout || "",
              stderr: execError.stderr || execError.message,
              success: false,
              exitCode: execError.code,
            },
            null,
            2
          ),
        },
      ],
    };
  }
}

// 启动服务器
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);

  // 这行很重要：让进程保持运行
  console.error("Custom AI MCP Server started");
}

main().catch((error) => {
  console.error("Server failed to start:", error);
  process.exit(1);
});
