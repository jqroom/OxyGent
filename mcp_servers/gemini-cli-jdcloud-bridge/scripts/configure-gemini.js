#!/usr/bin/env node

/**
 * Gemini CLI 配置脚本
 * 自动配置 Gemini CLI 使用项目的 MCP 服务器
 */

import { copyFileSync, existsSync, mkdirSync, writeFileSync } from "fs";
import { homedir } from "os";
import { dirname, join, resolve } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 配置常量
const PROJECT_ROOT = resolve(__dirname, "..");
const GEMINI_CONFIG_DIR = join(homedir(), ".gemini");
const GEMINI_CONFIG_FILE = join(GEMINI_CONFIG_DIR, "settings.json");
const MCP_SERVER_PATH = join(PROJECT_ROOT, "dist", "index.js");

// 默认配置模板
const GEMINI_CONFIG_TEMPLATE = {
  mcpServers: {
    "custom-ai-bridge": {
      command: "node",
      args: [MCP_SERVER_PATH],
      env: {
        NEXT_PUBLIC_AI_API_URL: "http://ai-api.custom.com/v1",
        NEXT_PUBLIC_AI_MODEL: "Claude-sonnet-4",
      },
    },
  },
  model: "gemini-2.0-flash-exp",
  systemPrompt:
    "你现在可以通过 custom-ai-bridge MCP 服务器访问京东云 AI 功能。使用 chat_completion 工具进行对话，使用 analyze_code 工具分析代码。",
  temperature: 0.7,
  maxTokens: 20000,
};

/**
 * 创建 Gemini 配置目录
 */
function ensureGeminiConfigDir() {
  if (!existsSync(GEMINI_CONFIG_DIR)) {
    console.log(`📁 创建 Gemini 配置目录: ${GEMINI_CONFIG_DIR}`);
    mkdirSync(GEMINI_CONFIG_DIR, { recursive: true });
  }
}

/**
 * 备份现有配置
 */
function backupExistingConfig() {
  if (existsSync(GEMINI_CONFIG_FILE)) {
    const backupFile = `${GEMINI_CONFIG_FILE}.backup.${Date.now()}`;
    console.log(`📄 备份现有配置到: ${backupFile}`);
    copyFileSync(GEMINI_CONFIG_FILE, backupFile);
    return true;
  }
  return false;
}

/**
 * 写入新配置
 */
function writeGeminiConfig() {
  console.log(`✍️  写入 Gemini CLI 配置: ${GEMINI_CONFIG_FILE}`);
  writeFileSync(
    GEMINI_CONFIG_FILE,
    JSON.stringify(GEMINI_CONFIG_TEMPLATE, null, 2)
  );
}

/**
 * 验证 MCP 服务器文件是否存在
 */
function validateMcpServer() {
  if (!existsSync(MCP_SERVER_PATH)) {
    console.error(`❌ MCP 服务器文件不存在: ${MCP_SERVER_PATH}`);
    console.error("请先运行 npm run build 构建项目");
    process.exit(1);
  }
  console.log(`✅ MCP 服务器文件已找到: ${MCP_SERVER_PATH}`);
}

/**
 * 主函数
 */
function main() {
  console.log("🚀 配置 Gemini CLI 使用项目 MCP 服务器...\n");

  try {
    // 验证 MCP 服务器
    validateMcpServer();

    // 创建配置目录
    ensureGeminiConfigDir();

    // 备份现有配置
    const hasBackup = backupExistingConfig();
    if (hasBackup) {
      console.log("⚠️  检测到现有配置，已自动备份");
    }

    // 写入新配置
    writeGeminiConfig();

    console.log("\n🎉 Gemini CLI 配置完成！");
    console.log("\n📋 下一步操作：");
    console.log("1. 确保项目 AI 服务正在运行 (http://localhost:3000)");
    console.log("2. 运行 gemini 命令开始使用");
    console.log("\n🔧 配置文件位置：");
    console.log(`   - Gemini CLI: ${GEMINI_CONFIG_FILE}`);
    console.log(`   - MCP 服务器: ${MCP_SERVER_PATH}`);
  } catch (error) {
    console.error("❌ 配置失败:", error.message);
    process.exit(1);
  }
}

// 运行主函数
main();

export default {
  main,
  GEMINI_CONFIG_TEMPLATE,
  MCP_SERVER_PATH,
};
