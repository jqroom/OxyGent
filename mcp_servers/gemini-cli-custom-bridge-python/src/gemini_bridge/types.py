"""
类型定义模块
定义所有接口、数据结构和类型
"""

from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: Literal["system", "user", "assistant"]
    content: str


class ProjectMessage(BaseModel):
    """项目消息模型"""
    role: Literal["system", "user", "assistant"]
    content: str
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AIConfig(BaseModel):
    """AI 配置模型"""
    api_url: str
    model: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 2000


class ChatCompletionArgs(BaseModel):
    """聊天完成请求参数"""
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000
    stream: Optional[bool] = False


class CodeAnalysisArgs(BaseModel):
    """代码分析请求参数"""
    code: str
    language: Optional[str] = None
    analysis_type: Literal["review", "optimize", "explain", "debug", "quality"] = "review"


class ReadFileArgs(BaseModel):
    """读取文件参数"""
    path: str


class WriteFileArgs(BaseModel):
    """写入文件参数"""
    path: str
    content: str


class ListFilesArgs(BaseModel):
    """列出文件参数"""
    path: Optional[str] = None


class ReadManyFilesArgs(BaseModel):
    """批量读取文件参数"""
    paths: List[str]
    include_path_in_response: Optional[bool] = True


class ExecuteCommandArgs(BaseModel):
    """执行命令参数"""
    command: str
    cwd: Optional[str] = None


class GrepArgs(BaseModel):
    """Grep 搜索参数"""
    pattern: str
    path: Optional[str] = "."
    recursive: Optional[bool] = False
    ignore_case: Optional[bool] = False
    line_numbers: Optional[bool] = True


class GlobArgs(BaseModel):
    """Glob 模式匹配参数"""
    pattern: str
    base_path: Optional[str] = "."


class EditOperation(BaseModel):
    """编辑操作"""
    type: Literal["replace_line", "insert_line", "delete_line"]
    line_number: int
    new_content: Optional[str] = None


class EditArgs(BaseModel):
    """文件编辑参数"""
    path: str
    # 支持两种格式：新格式(operations列表)和旧格式(单个operation+content)
    operations: Optional[List[EditOperation]] = None
    operation: Optional[str] = None
    content: Optional[str] = None
    
    def model_post_init(self, __context) -> None:
        """后处理：将旧格式转换为新格式"""
        if self.operations is None and self.operation is not None:
            # 如果使用旧格式，转换为新格式
            if self.operation == "replace":
                # 对于replace操作，如果content包含多行，则替换整个文件内容
                content = self.content or ""
                if '\n' in content or len(content) > 100:
                    # 内容较长或包含换行符，视为整个文件替换
                    # 创建一个特殊的操作来标识这是文件内容替换
                    operation_obj = EditOperation(
                        type="replace_line",
                        line_number=-1,  # 使用-1表示替换整个文件
                        new_content=content
                    )
                else:
                    # 短内容，替换第一行
                    operation_obj = EditOperation(
                        type="replace_line",
                        line_number=1,
                        new_content=content
                    )
            elif self.operation == "insert":
                operation_obj = EditOperation(
                    type="insert_line",
                    line_number=1,
                    new_content=self.content or ""
                )
            elif self.operation == "delete":
                operation_obj = EditOperation(
                    type="delete_line",
                    line_number=1
                )
            else:
                # 默认处理为replace
                operation_obj = EditOperation(
                    type="replace_line",
                    line_number=1,
                    new_content=self.content or ""
                )
            
            self.operations = [operation_obj]


class WebFetchArgs(BaseModel):
    """网络获取参数"""
    url: str
    method: Optional[Literal["GET", "POST", "PUT", "DELETE"]] = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[str] = None


class WebSearchArgs(BaseModel):
    """网络搜索参数"""
    query: str
    num_results: Optional[int] = 5


class MemoryArgs(BaseModel):
    """内存操作参数"""
    operation: Literal["store", "retrieve", "delete", "list"]
    key: Optional[str] = None
    value: Optional[str] = None
    tags: Optional[List[str]] = None


# API 响应类型定义
class AIResponse(BaseModel):
    """AI API 响应基础模型"""
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """聊天完成响应"""
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None


class StreamChunk(BaseModel):
    """流式响应块"""
    type: Literal["chunk", "done", "error"]
    content: Optional[str] = None
    done: bool = False
    chunk_index: Optional[int] = None
    error: Optional[str] = None


# 路径验证相关类型
class PathValidationResult(BaseModel):
    """路径验证结果"""
    is_valid: bool
    absolute_path: str
    error_message: Optional[str] = None


class PathValidationOptions(BaseModel):
    """路径验证选项"""
    allow_exact_temp_dir: bool = True
    create_directory_if_not_exists: bool = False


# 工具执行结果类型
class ToolResult(BaseModel):
    """工具执行结果"""
    content: List[Dict[str, Any]]
    is_error: Optional[bool] = False
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="_meta")

    class Config:
        allow_population_by_field_name = True


class FileInfo(BaseModel):
    """文件信息"""
    name: str
    type: Literal["file", "directory"]
    size: Optional[int] = None
    modified: Optional[str] = None


class CommandResult(BaseModel):
    """命令执行结果"""
    stdout: str
    stderr: str
    success: bool
    exit_code: Optional[int] = None
    working_directory: Optional[str] = None


class GrepResult(BaseModel):
    """Grep 搜索结果"""
    file: str
    line_number: int
    line_content: str
    match_start: int
    match_end: int
    matched_text: str


class WebContent(BaseModel):
    """网页内容"""
    url: str
    content: str
    status_code: int
    headers: Dict[str, str]
    content_type: str
    encoding: str
    size: int
    truncated: bool = False


class MemoryEntry(BaseModel):
    """内存条目"""
    key: str
    value: str
    timestamp: str
    tags: List[str] = Field(default_factory=list)


# 配置相关类型
class ServerConfig(BaseModel):
    """服务器配置"""
    name: str = "gemini-cli-custom-bridge-python"
    version: str = "1.0.0"
    description: str = "Python version of Gemini CLI Custom Bridge MCP Server"
    
    # AI 配置
    ai_api_url: str
    ai_model: str
    ai_api_key: str
    
    # 路径配置
    temp_dir: str
    project_root: str
    
    # 服务配置
    timeout: int = 30
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_extensions: List[str] = Field(default_factory=lambda: [
        ".js", ".ts", ".jsx", ".tsx", ".py", ".java", ".c", ".cpp", ".h", ".hpp",
        ".cs", ".php", ".rb", ".go", ".rs", ".swift", ".kt", ".scala", ".clj",
        ".hs", ".ml", ".fs", ".vb", ".pl", ".sh", ".bat", ".ps1", ".html", ".htm",
        ".xml", ".svg", ".md", ".markdown", ".rst", ".tex", ".css", ".scss",
        ".sass", ".less", ".styl", ".json", ".yaml", ".yml", ".toml", ".ini",
        ".cfg", ".conf", ".config", ".csv", ".tsv", ".sql", ".db", ".sqlite",
        ".txt", ".log", ".readme", ".license", ".changelog", ".ejs", ".hbs",
        ".mustache", ".twig", ".jinja", ".liquid", ".gitignore", ".gitattributes",
        ".editorconfig", ".prettierrc", ".eslintrc", ".babelrc", ".npmrc",
        ".nvmrc", ".dockerignore", ".htaccess"
    ])
    
    valid_hidden_files: List[str] = Field(default_factory=lambda: [
        ".env", ".gitignore", ".gitattributes", ".editorconfig", ".prettierrc",
        ".eslintrc", ".babelrc", ".npmrc", ".nvmrc", ".dockerignore", ".htaccess",
        ".bashrc", ".zshrc", ".vimrc", ".tmux", ".profile", ".bashprofile"
    ])


# 异常类型
class PathSecurityError(Exception):
    """路径安全错误"""
    pass


class AIAPIError(Exception):
    """AI API 错误"""
    pass


class ToolExecutionError(Exception):
    """工具执行错误"""
    pass


class FileOperationError(Exception):
    """文件操作错误"""
    pass