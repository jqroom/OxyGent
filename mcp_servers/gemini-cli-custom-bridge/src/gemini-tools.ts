/**
 * Gemini CLI Built-in Tools 扩展模块
 * 实现 Gemini CLI 的内置工具功能
 */

import fs from "fs/promises";
import { glob as globSync } from "glob";
import fetch from "node-fetch";
import path from "path";
import { resolveSafePath } from "./path-manager.js";

// 工具参数类型定义
export interface GrepArgs {
  pattern: string;
  path?: string;
  recursive?: boolean;
  case_insensitive?: boolean;
  line_numbers?: boolean;
}

export interface GlobArgs {
  pattern: string;
  cwd?: string;
}

export interface EditArgs {
  path: string;
  operation: "replace" | "insert" | "delete";
  line_number?: number;
  old_text?: string;
  new_text?: string;
  content?: string;
}

export interface WebFetchArgs {
  url: string;
  method?: "GET" | "POST" | "PUT" | "DELETE";
  headers?: Record<string, string>;
  body?: string;
}

export interface WebSearchArgs {
  query: string;
  num_results?: number;
}

export interface MemoryArgs {
  operation: "get" | "set" | "delete" | "list";
  key?: string;
  value?: string;
}

// 内存存储（简单的内存实现）
const memoryStore = new Map<string, string>();

/**
 * Grep 工具实现 - 在文件中搜索模式
 */
export const handleGrepTool = async (args: GrepArgs) => {
  const {
    pattern,
    path: searchPath = ".",
    recursive = false,
    case_insensitive = false,
    line_numbers = true,
  } = args;

  try {
    const safePath = resolveSafePath(searchPath);
    const stats = await fs.stat(safePath);

    let results: string[] = [];

    if (stats.isFile()) {
      // 搜索单个文件
      const content = await fs.readFile(safePath, "utf-8");
      const grepResults = searchInContent(
        content,
        pattern,
        case_insensitive,
        line_numbers,
        safePath
      );
      results = grepResults;
    } else if (stats.isDirectory()) {
      // 搜索目录
      const files = await getFilesRecursively(safePath, recursive);
      for (const file of files) {
        try {
          const content = await fs.readFile(file, "utf-8");
          const grepResults = searchInContent(
            content,
            pattern,
            case_insensitive,
            line_numbers,
            file
          );
          results.push(...grepResults);
        } catch {
          // 跳过无法读取的文件
          continue;
        }
      }
    }

    return {
      content: [
        {
          type: "text" as const,
          text: results.length > 0 ? results.join("\n") : "No matches found",
        },
      ],
    };
  } catch (error) {
    throw new Error(
      `Grep failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
};

/**
 * Glob 工具实现 - 文件模式匹配
 */
export const handleGlobTool = async (args: GlobArgs) => {
  const { pattern, cwd = "." } = args;

  try {
    const safeCwd = resolveSafePath(cwd);

    // 使用 glob 库进行文件匹配
    const matches = await globSync(pattern, { cwd: safeCwd });

    return {
      content: [
        {
          type: "text" as const,
          text:
            matches.length > 0
              ? matches.join("\n")
              : "No files matched the pattern",
        },
      ],
    };
  } catch (error) {
    throw new Error(
      `Glob failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
};

/**
 * Edit 工具实现 - 文件编辑操作
 */
export const handleEditTool = async (args: EditArgs) => {
  const {
    path: filePath,
    operation,
    line_number,
    old_text,
    new_text,
    content,
  } = args;

  try {
    const safePath = resolveSafePath(filePath);

    switch (operation) {
      case "replace":
        if (!old_text || !new_text) {
          throw new Error("Replace operation requires old_text and new_text");
        }
        await replaceInFile(safePath, old_text, new_text);
        break;

      case "insert":
        if (line_number === undefined || !content) {
          throw new Error("Insert operation requires line_number and content");
        }
        await insertInFile(safePath, line_number, content);
        break;

      case "delete":
        if (line_number === undefined) {
          throw new Error("Delete operation requires line_number");
        }
        await deleteFromFile(safePath, line_number);
        break;

      default:
        throw new Error(`Unknown edit operation: ${operation}`);
    }

    return {
      content: [
        {
          type: "text" as const,
          text: `File ${filePath} edited successfully using ${operation} operation`,
        },
      ],
    };
  } catch (error) {
    throw new Error(
      `Edit failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
};

/**
 * Web Fetch 工具实现 - 获取网络内容
 */
export const handleWebFetchTool = async (args: WebFetchArgs) => {
  const { url, method = "GET", headers = {}, body } = args;

  try {
    const response = await fetch(url, {
      method,
      headers: {
        "User-Agent": "AutoDev-Assistant/1.0",
        ...headers,
      },
      body: body && method !== "GET" ? body : undefined,
    });

    const content = await response.text();
    const responseHeaders = Object.fromEntries(response.headers.entries());

    return {
      content: [
        {
          type: "text" as const,
          text: `Status: ${response.status} ${
            response.statusText
          }\n\nHeaders:\n${JSON.stringify(
            responseHeaders,
            null,
            2
          )}\n\nContent:\n${content}`,
        },
      ],
    };
  } catch (error) {
    throw new Error(
      `Web fetch failed: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
};

/**
 * Web Search 工具实现 - 网络搜索（简化版本）
 */
export const handleWebSearchTool = async (args: WebSearchArgs) => {
  const { query, num_results = 5 } = args;

  try {
    // 这里使用 DuckDuckGo 的即时搜索 API 作为示例
    // 实际项目中可以集成更专业的搜索 API
    const searchUrl = `https://api.duckduckgo.com/?q=${encodeURIComponent(
      query
    )}&format=json&no_html=1&skip_disambig=1`;

    const response = await fetch(searchUrl);
    const data = (await response.json()) as {
      AbstractText?: string;
      RelatedTopics?: Array<{
        Text?: string;
        FirstURL?: string;
      }>;
    };

    // 格式化搜索结果
    const results = [];
    if (data.AbstractText) {
      results.push(`Abstract: ${data.AbstractText}`);
    }

    if (data.RelatedTopics && data.RelatedTopics.length > 0) {
      results.push("\nRelated Topics:");
      data.RelatedTopics.slice(0, num_results).forEach(
        (topic, index: number) => {
          if (topic.Text) {
            results.push(`${index + 1}. ${topic.Text}`);
            if (topic.FirstURL) {
              results.push(`   URL: ${topic.FirstURL}`);
            }
          }
        }
      );
    }

    return {
      content: [
        {
          type: "text" as const,
          text:
            results.length > 0 ? results.join("\n") : "No search results found",
        },
      ],
    };
  } catch (error) {
    throw new Error(
      `Web search failed: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
};

/**
 * Memory 工具实现 - 内存管理
 */
export const handleMemoryTool = async (args: MemoryArgs) => {
  const { operation, key, value } = args;

  try {
    switch (operation) {
      case "get":
        if (!key) throw new Error("Get operation requires key");
        const getValue = memoryStore.get(key);
        return {
          content: [
            {
              type: "text" as const,
              text: getValue || `No value found for key: ${key}`,
            },
          ],
        };

      case "set":
        if (!key || value === undefined) {
          throw new Error("Set operation requires key and value");
        }
        memoryStore.set(key, value);
        return {
          content: [
            {
              type: "text" as const,
              text: `Memory key '${key}' set successfully`,
            },
          ],
        };

      case "delete":
        if (!key) throw new Error("Delete operation requires key");
        const deleted = memoryStore.delete(key);
        return {
          content: [
            {
              type: "text" as const,
              text: deleted
                ? `Memory key '${key}' deleted successfully`
                : `Key '${key}' not found`,
            },
          ],
        };

      case "list":
        const keys = Array.from(memoryStore.keys());
        return {
          content: [
            {
              type: "text" as const,
              text:
                keys.length > 0
                  ? `Memory keys: ${keys.join(", ")}`
                  : "No memory keys found",
            },
          ],
        };

      default:
        throw new Error(`Unknown memory operation: ${operation}`);
    }
  } catch (error) {
    throw new Error(
      `Memory operation failed: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
};

// 辅助函数

/**
 * 在内容中搜索模式
 */
const searchInContent = (
  content: string,
  pattern: string,
  caseInsensitive: boolean,
  lineNumbers: boolean,
  filePath: string
): string[] => {
  const lines = content.split("\n");
  const regex = new RegExp(pattern, caseInsensitive ? "gi" : "g");
  const results: string[] = [];

  lines.forEach((line, index) => {
    if (regex.test(line)) {
      const lineNum = index + 1;
      const prefix = lineNumbers ? `${filePath}:${lineNum}:` : `${filePath}:`;
      results.push(`${prefix} ${line}`);
    }
  });

  return results;
};

/**
 * 递归获取文件列表
 */
const getFilesRecursively = async (
  dirPath: string,
  recursive: boolean
): Promise<string[]> => {
  const files: string[] = [];
  const entries = await fs.readdir(dirPath, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dirPath, entry.name);

    if (entry.isFile()) {
      files.push(fullPath);
    } else if (entry.isDirectory() && recursive) {
      const subFiles = await getFilesRecursively(fullPath, recursive);
      files.push(...subFiles);
    }
  }

  return files;
};

/**
 * 在文件中替换文本
 */
const replaceInFile = async (
  filePath: string,
  oldText: string,
  newText: string
) => {
  const content = await fs.readFile(filePath, "utf-8");
  const updatedContent = content.replace(new RegExp(oldText, "g"), newText);
  await fs.writeFile(filePath, updatedContent, "utf-8");
};

/**
 * 在文件指定行插入内容
 */
const insertInFile = async (
  filePath: string,
  lineNumber: number,
  content: string
) => {
  const fileContent = await fs.readFile(filePath, "utf-8");
  const lines = fileContent.split("\n");

  // 插入到指定行之前（lineNumber - 1 是因为行号从1开始）
  lines.splice(lineNumber - 1, 0, content);

  await fs.writeFile(filePath, lines.join("\n"), "utf-8");
};

/**
 * 删除文件指定行
 */
const deleteFromFile = async (filePath: string, lineNumber: number) => {
  const content = await fs.readFile(filePath, "utf-8");
  const lines = content.split("\n");

  // 删除指定行（lineNumber - 1 是因为行号从1开始）
  if (lineNumber > 0 && lineNumber <= lines.length) {
    lines.splice(lineNumber - 1, 1);
    await fs.writeFile(filePath, lines.join("\n"), "utf-8");
  } else {
    throw new Error(`Line number ${lineNumber} is out of range`);
  }
};
