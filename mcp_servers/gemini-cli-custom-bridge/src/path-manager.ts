import path from "path";
import { fileURLToPath } from "url";

/**
 * 统一的路径管理模块
 * 负责管理和验证所有文件操作的路径安全性
 * 确保所有操作都限制在 autodev 项目根目录下的 temp 目录内
 *
 * 核心规则：
 * 1. 只允许访问和修改 autodev/temp 目录下的资源
 * 2. 相对路径均相对于 autodev/temp 目录
 * 3. 绝对路径必须是 autodev/temp 的子路径
 */

// 获取当前文件的目录路径（ES 模块中 __dirname 的替代方案）
const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * 路径配置常量
 */
export const PATH_CONFIG = {
  // AutoDev 项目根目录（gemini-cli-custom-bridge 的上级目录）
  PROJECT_ROOT: path.resolve(__dirname, "../.."),

  // 允许操作的 temp 目录
  get TEMP_DIR() {
    return path.join(this.PROJECT_ROOT, "temp");
  },

  // 路径分隔符
  PATH_SEP: path.sep,
} as const;

/**
 * 路径验证结果接口
 */
export interface PathValidationResult {
  isValid: boolean;
  absolutePath: string;
  errorMessage?: string;
}

/**
 * 路径验证选项
 */
export interface PathValidationOptions {
  allowExactTempDir?: boolean; // 是否允许访问 temp 目录本身
  createDirectoryIfNotExists?: boolean; // 是否在目录不存在时创建
}

/**
 * 统一的路径验证函数
 * 核心逻辑：所有路径都必须在 autodev/temp 目录内
 * @param inputPath 输入的路径（可以是相对路径或绝对路径）
 * @param options 验证选项
 * @returns 路径验证结果
 */
export const validatePath = (
  inputPath: string,
  options: PathValidationOptions = {}
): PathValidationResult => {
  const { allowExactTempDir = true } = options;

  console.error(`[PATH_MANAGER] 开始验证路径: "${inputPath}"`);
  console.error(`[PATH_MANAGER] 项目根目录: "${PATH_CONFIG.PROJECT_ROOT}"`);
  console.error(`[PATH_MANAGER] 允许的temp目录: "${PATH_CONFIG.TEMP_DIR}"`);

  try {
    let absolutePath: string;

    // 检查是否为绝对路径
    if (path.isAbsolute(inputPath)) {
      // 绝对路径：直接使用，但必须在 temp 目录内
      absolutePath = path.normalize(inputPath);
      console.error(`[PATH_MANAGER] 处理绝对路径: "${absolutePath}"`);
    } else {
      // 相对路径处理
      // 处理特殊情况
      if (inputPath === "." || inputPath === "./") {
        // 当前目录指向 temp 目录
        absolutePath = PATH_CONFIG.TEMP_DIR;
        console.error(`[PATH_MANAGER] 当前目录指向temp目录: "${absolutePath}"`);
      } else {
        // 清理路径前缀
        const cleanPath = inputPath.replace(/^\.\//, "");

        // 修复路径解析逻辑：区分不同的temp路径情况
        if (cleanPath === "temp") {
          // "./temp" 或 "temp" 应该指向temp目录本身
          absolutePath = PATH_CONFIG.TEMP_DIR;
          console.error(
            `[PATH_MANAGER] temp目录本身: "${cleanPath}" -> "${absolutePath}"`
          );
        } else if (cleanPath.startsWith("temp/")) {
          // "temp/xxx" 应该指向temp目录下的子路径
          absolutePath = path.resolve(PATH_CONFIG.PROJECT_ROOT, cleanPath);
          console.error(
            `[PATH_MANAGER] temp子路径，相对于项目根目录解析: "${cleanPath}" -> "${absolutePath}"`
          );
        } else {
          // 其他相对路径相对于 temp 目录解析
          absolutePath = path.resolve(PATH_CONFIG.TEMP_DIR, cleanPath);
          console.error(
            `[PATH_MANAGER] 相对路径相对于temp目录解析: "${cleanPath}" -> "${absolutePath}"`
          );
        }
      }
    }

    // 规范化路径
    absolutePath = path.normalize(absolutePath);
    console.error(`[PATH_MANAGER] 规范化后的路径: "${absolutePath}"`);

    // 检查路径是否在允许的范围内
    const normalizedTempDir = path.normalize(PATH_CONFIG.TEMP_DIR);

    // 使用 path.relative 来检查路径关系，这是更可靠的方法
    const relativePath = path.relative(normalizedTempDir, absolutePath);

    // 如果相对路径以 '..' 开头，说明目标路径在temp目录外部
    // 如果相对路径为空字符串，说明是temp目录本身
    // 如果相对路径不以 '..' 开头且不为空，说明在temp目录内部
    const isWithinTempDir =
      relativePath !== "" &&
      !relativePath.startsWith(".." + PATH_CONFIG.PATH_SEP) &&
      !relativePath.startsWith("..");
    const isExactTempDir = relativePath === "";

    console.error(`[PATH_MANAGER] 路径验证检查:`);
    console.error(`[PATH_MANAGER]   - 标准化temp目录: ${normalizedTempDir}`);
    console.error(`[PATH_MANAGER]   - 目标绝对路径: ${absolutePath}`);
    console.error(`[PATH_MANAGER]   - 相对路径: "${relativePath}"`);
    console.error(`[PATH_MANAGER]   - 在temp目录内: ${isWithinTempDir}`);
    console.error(`[PATH_MANAGER]   - 是temp目录本身: ${isExactTempDir}`);
    console.error(
      `[PATH_MANAGER]   - 允许访问temp目录本身: ${allowExactTempDir}`
    );

    // 验证路径安全性：必须在 temp 目录内或者是 temp 目录本身（如果允许）
    if (!isWithinTempDir && !(isExactTempDir && allowExactTempDir)) {
      const errorMessage = `访问被拒绝: 路径必须在 ${normalizedTempDir} 目录内。尝试访问的路径: ${inputPath} (解析为: ${absolutePath}, 相对路径: ${relativePath})`;
      console.error(`[PATH_MANAGER] 验证失败: ${errorMessage}`);

      return {
        isValid: false,
        absolutePath,
        errorMessage,
      };
    }

    console.error(`[PATH_MANAGER] 路径验证通过: "${absolutePath}"`);

    return {
      isValid: true,
      absolutePath,
    };
  } catch (error) {
    const errorMessage = `路径验证过程中发生错误: ${
      error instanceof Error ? error.message : String(error)
    }`;
    console.error(`[PATH_MANAGER] 验证异常: ${errorMessage}`);

    return {
      isValid: false,
      absolutePath: inputPath,
      errorMessage,
    };
  }
};

/**
 * 验证工作目录路径
 * @param cwd 工作目录路径（可选，默认使用 temp 目录）
 * @returns 路径验证结果
 */
export const validateWorkingDirectory = (
  cwd?: string
): PathValidationResult => {
  console.error(`[PATH_MANAGER] 开始验证工作目录: "${cwd || "undefined"}"`);

  // 如果没有提供工作目录，使用默认的 temp 目录
  const workDir = cwd || ".";
  console.error(`[PATH_MANAGER] 使用工作目录: "${workDir}"`);

  return validatePath(workDir, { allowExactTempDir: true });
};

/**
 * 安全的路径解析函数
 * 在验证路径安全性后返回绝对路径，如果验证失败则抛出错误
 * @param inputPath 输入路径
 * @param options 验证选项
 * @returns 安全的绝对路径
 * @throws Error 如果路径验证失败
 */
export const resolveSafePath = (
  inputPath: string,
  options?: PathValidationOptions
): string => {
  const result = validatePath(inputPath, options);

  if (!result.isValid) {
    throw new Error(result.errorMessage || "路径验证失败");
  }

  return result.absolutePath;
};

/**
 * 安全的工作目录解析函数
 * @param cwd 工作目录路径（可选）
 * @returns 安全的工作目录绝对路径
 * @throws Error 如果路径验证失败
 */
export const resolveSafeWorkingDirectory = (cwd?: string): string => {
  const result = validateWorkingDirectory(cwd);

  if (!result.isValid) {
    throw new Error(result.errorMessage || "工作目录验证失败");
  }

  return result.absolutePath;
};

/**
 * 获取相对于 temp 目录的路径
 * @param absolutePath 绝对路径
 * @returns 相对于 temp 目录的路径
 */
export const getRelativeToTempDir = (absolutePath: string): string => {
  return path.relative(PATH_CONFIG.TEMP_DIR, absolutePath);
};

/**
 * 路径管理器单例类
 * 提供统一的路径管理接口
 */
export class PathManager {
  private static instance: PathManager;

  private constructor() {}

  public static getInstance(): PathManager {
    if (!PathManager.instance) {
      PathManager.instance = new PathManager();
    }
    return PathManager.instance;
  }

  /**
   * 验证路径
   */
  public validatePath(
    inputPath: string,
    options?: PathValidationOptions
  ): PathValidationResult {
    return validatePath(inputPath, options);
  }

  /**
   * 解析安全路径
   */
  public resolveSafePath(
    inputPath: string,
    options?: PathValidationOptions
  ): string {
    return resolveSafePath(inputPath, options);
  }

  /**
   * 验证工作目录
   */
  public validateWorkingDirectory(cwd?: string): PathValidationResult {
    return validateWorkingDirectory(cwd);
  }

  /**
   * 解析安全工作目录
   */
  public resolveSafeWorkingDirectory(cwd?: string): string {
    return resolveSafeWorkingDirectory(cwd);
  }

  /**
   * 获取配置
   */
  public getConfig() {
    return PATH_CONFIG;
  }
}

// 导出默认实例
export const pathManager = PathManager.getInstance();
