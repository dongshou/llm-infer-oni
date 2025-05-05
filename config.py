"""
AI-UI-Controller 配置文件
定义系统的各项配置参数
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()  # 默认加载项目根目录的 .env 文件

# 系统配置
CONFIG = {
    # ===== 基本配置 =====
    # "app_title": "Oxygen Not Included",  # 应用窗口标题
    # "app_name": "OxygenNotIncluded", 
    
    # 最大迭代次数，超过此次数将自动停止
    "max_iterations": 100,
    
    # 每次迭代之间的延迟时间(秒)
    "iteration_delay": 0.5,
    
    # ===== API配置 =====
    # 大模型API密钥（需要替换为你的真实密钥）
    "api_key":os.getenv("api_key"),
    
    # 使用的模型名称
    "model": "o4-mini",
    
    # API端点URL
    "base_url": os.getenv('base_url'),
    
    # API请求参数
    # "max_tokens": 1024,
    "temperature": 0.7,
    
    # ===== 操作配置 =====
    # 默认操作延迟(秒)  
    "action_delay": 1.0,
    
    # 特定操作类型的延迟设置
    "action_delays": {
        "move": 0.1,      # 移动鼠标
        "click": 0.1,     # 点击鼠标
        "type": 0.2,      # 输入文本
        "key": 0.1,       # 按键操作
        "scroll": 0.2     # 滚动操作
    },
    # ===== 提示词配置 =====
    # 提示词存储目录
    "prompt_dir": os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts"),
    
    # 默认使用的提示词名称
    "default_prompt_name": "oxygen_not_included",
    
    # 可用的提示词名称列表（程序会从prompt_dir目录中加载这些文件）
    "prompt_names": [
        "default",     # 基本提示词
        "browser",     # 浏览器操作专用提示词
        "text_input",  # 文本输入专用提示词
        "office"       # 办公软件专用提示词
    ],
    
    # 任务类型到提示词的映射
    "task_prompt_mapping": {
        "browser": ["浏览器", "网页", "搜索", "chrome", "firefox", "edge"],
        "text_input": ["输入", "文本", "填写", "表单"],
        "office": ["excel", "word", "powerpoint", "文档", "表格", "演示"]
    },
    
    # 鼠标移动持续时间
    "move_duration": 0.1,
    
    # 键盘输入间隔时间
    "type_interval": 0.1,
    
    # PyAutoGUI安全暂停时间
    "pyautogui_pause": 0.1,
    
    # 屏幕捕获最小间隔(秒)
    "min_capture_interval": 0.2,
    
    # ===== 中间件配置 =====
    # 启用的中间件列表
    "middlewares": [
        "middlewares.logging_mw.LoggingMiddleware",
        "middlewares.throttling.ThrottlingMiddleware",
        "middlewares.state_tracking.StateTrackingMiddleware",
        "middlewares.screenshot_logger.ScreenshotLoggerMiddleware"  # 新添加的截图记录中间件

    ],
    
    # ===== 截图记录中间件配置 =====
    "screenshot_logger_enabled": True,
    "screenshot_log_dir": "logs/screenshots",
    "screenshot_log_frequency": 1,  # 每N步保存一次截图，1表示每步都保存
    "screenshot_save_raw": True,    # 是否保存原始图像
    "screenshot_save_base64": False, # 是否在日志中保存base64编码（会导致日志文件变大）
    
    # 保留的历史记录条数
    "max_history": 10,
    
    # 是否追踪统计信息
    "track_stats": True,
    
    # 是否追踪操作时长
    "track_duration": True,
    
    # 是否记录详细的操作信息
    "log_details": True,
    
    # ===== 日志配置 =====
    # 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
    "log_level": "INFO",
    
    # 日志文件路径（None表示仅输出到控制台）
    "log_file": "logs/ai_controller",
    
    # 日志轮转设置
    "rotation": "1 day",
    "retention": "7 days",
    "compression": "zip",
    
    # 日志格式
    "log_format": "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
}

# 开发环境配置，继承基本配置并覆盖部分选项
DEV_CONFIG = {
    **CONFIG,
    "log_level": "DEBUG",
    "max_iterations": 20,
    "iteration_delay": 0.2,
    "log_details": True
}

# 测试环境配置
TEST_CONFIG = {
    **CONFIG,
    "log_level": "DEBUG",
    "max_iterations": 50,
    "log_file": "logs/test_ai_controller"
}

# 生产环境配置
PROD_CONFIG = {
    **CONFIG,
    "log_level": "INFO",
    "max_iterations": 200,
    "log_details": False,
    "track_stats": True
}

def get_config(env="prod"):
    """获取指定环境的配置
    
    Args:
        env (str): 环境名称，支持 "dev", "test", "prod"
        
    Returns:
        dict: 配置字典
    """
    if env.lower() == "dev":
        return DEV_CONFIG
    elif env.lower() == "test":
        return TEST_CONFIG
    elif env.lower() == "prod":
        return PROD_CONFIG
    else:
        return CONFIG