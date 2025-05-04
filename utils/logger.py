"""
日志配置模块 - 配置loguru日志系统
"""

import os
import sys
import time
from loguru import logger

def setup_logger(config=None):
    """配置loguru日志系统
    
    Args:
        config (dict, optional): 日志配置参数
            - log_level: 日志级别 (默认 "INFO")
            - log_format: 日志格式 (默认包含时间、级别、消息)
            - log_file: 日志文件路径 (默认为None，仅控制台输出)
            - rotation: 日志轮转设置 (默认 "1 day")
            - retention: 日志保留时间 (默认 "7 days")
            - compression: 日志压缩格式 (默认 "zip")
    
    Returns:
        logger: 配置好的logger对象
    """
    # 默认配置
    config = config or {}
    log_level = config.get("log_level", "INFO")
    log_format = config.get("log_format", 
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>")
    
    # 移除默认的handler
    logger.remove()
    
    # 添加控制台handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # 如果指定了日志文件，添加文件handler
    log_file = config.get("log_file")
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 如果没有扩展名，添加日期和.log扩展名
        if not os.path.splitext(log_file)[1]:
            date_str =  time.strftime("%Y%m%d%H%M")
            log_file = f"{log_file}_{date_str}.log"
            
        # 添加文件handler
        logger.add(
            log_file,
            format=log_format,
            level=log_level,
            rotation=config.get("rotation", "1 day"),
            retention=config.get("retention", "7 days"),
            compression=config.get("compression", "zip"),
            encoding="utf-8"
        )
        
        logger.info("日志文件配置完成: {}", log_file)
    
    logger.info("日志系统配置完成，级别: {}", log_level)
    return logger

def get_logger():
    """获取配置好的logger对象
    
    Returns:
        logger: logger对象
    """
    return logger

# 辅助函数，用于格式化异常信息
def format_exception(e):
    """格式化异常信息
    
    Args:
        e (Exception): 异常对象
        
    Returns:
        str: 格式化后的异常信息
    """
    import traceback
    return f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

# 辅助函数，用于格式化时间
def format_time(seconds):
    """将秒数格式化为可读时间
    
    Args:
        seconds (float): 秒数
        
    Returns:
        str: 格式化后的时间字符串
    """
    if seconds < 0.001:  # 小于1毫秒
        return f"{seconds*1000000:.2f}微秒"
    elif seconds < 1:    # 小于1秒
        return f"{seconds*1000:.2f}毫秒"
    elif seconds < 60:   # 小于1分钟
        return f"{seconds:.2f}秒"
    elif seconds < 3600: # 小于1小时
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}分{secs:.2f}秒"
    else:                # 大于等于1小时
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}时{minutes}分{secs:.2f}秒"