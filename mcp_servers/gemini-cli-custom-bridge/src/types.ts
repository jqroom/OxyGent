// 消息类型定义 - 兼容项目的Message接口
export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

// 项目Message接口定义
export interface ProjectMessage {
  id: string;
  role: "system" | "user" | "assistant";
  content: string;
  timestamp: Date;
}

// AI配置接口
export interface AIConfig {
  provider: string;
  model: string;
  temperature: number;
  maxTokens: number;
  apiKey: string;
  baseUrl: string;
}

// 聊天完成请求参数
export interface ChatCompletionArgs {
  messages: ChatMessage[];
  model?: string;
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
}

// 项目ChatRequest接口
export interface ProjectChatRequest {
  messages: ProjectMessage[];
  config: AIConfig;
  systemPrompt?: string;
  repositoryContext?: string;
  stream?: boolean;
}

// 代码分析请求参数
export interface CodeAnalysisArgs {
  code: string;
  language?: string;
  analysis_type?: "review" | "optimize" | "explain" | "debug";
}

// API 响应类型
export interface APIResponse {
  choices?: Array<{
    message?: {
      content: string;
    };
    delta?: {
      content?: string;
    };
  }>;
  content?: string;
  error?: string;
}
