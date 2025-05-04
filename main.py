#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI-UI-Controller 主程序入口
用于启动和控制AI驱动的UI自动化系统
"""

import os
import sys
import time
import argparse
import traceback
from loguru import logger

from config import get_config
from utils.logger import setup_logger
from core.ui_agent import UIAgent


def parse_arguments():
    """解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(
        description="llm-infer-oni: 基于缺氧游戏提高大模型的推理能力",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "task", 
        nargs="?", 
        default="建造一个制氧设备",
        help="要执行的任务描述，例如: '打开浏览器并搜索Python'"
    )
    
     # 添加提示词相关参数
    parser.add_argument(
        "-p", "--prompt", 
        help="使用指定的提示词，可以是名称或文件路径"
    )
    
    parser.add_argument(
        "--list-prompts", 
        action="store_true", 
        help="列出所有可用的提示词"
    )
    
    parser.add_argument(
        "--auto-prompt", 
        action="store_true", 
        default=True,
        help="根据任务自动选择合适的提示词"
    )
    
    parser.add_argument(
    "--base-url", 
    help="OpenAI API的自定义端点URL"
    )
    
    parser.add_argument(
        "-e", "--env", 
        choices=["dev", "test", "prod"], 
        default="dev", 
        help="运行环境: 开发(dev)、测试(test)或生产(prod)"
    )
    
    parser.add_argument(
        "-c", "--config", 
        help="自定义配置文件的路径"
    )
    
    parser.add_argument(
        "-i", "--iterations", 
        type=int, 
        help="最大迭代次数"
    )
    
    parser.add_argument(
        "-d", "--delay", 
        type=float, 
        help="迭代间延迟时间(秒)"
    )
    
    parser.add_argument(
        "-l", "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="日志级别"
    )
    
    parser.add_argument(
        "-k", "--api-key", 
        help="API密钥，会覆盖配置文件中的设置"
    )
    
    return parser.parse_args()


def load_custom_config(file_path):
    """加载自定义配置文件
    
    Args:
        file_path (str): 配置文件路径
        
    Returns:
        dict: 配置字典，加载失败则返回None
    """
    try:
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            # 尝试加载JSON格式
            if file_path.endswith('.json'):
                return json.load(f)
            
            # 尝试加载Python模块
            elif file_path.endswith('.py'):
                import importlib.util
                spec = importlib.util.spec_from_file_location("custom_config", file_path)
                custom_config = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(custom_config)
                
                if hasattr(custom_config, 'CONFIG'):
                    return custom_config.CONFIG
            
            logger.error("不支持的配置文件格式")
            return None
    
    except Exception as e:
        logger.error(f"加载配置文件出错: {e}")
        return None


def safe_get_task_from_input():
    """安全地从用户输入获取任务描述
    
    Returns:
        str: 任务描述
    """
    print("\n请输入要执行的任务描述 (Ctrl+C 取消):")
    try:
        return input("> ").strip()
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(0)
    except Exception as e:
        logger.error(f"获取输入出错: {e}")
        return None


def main():
    """主函数"""
    # 解析命令行参数
    args = parse_arguments()
    
    # 加载配置
    config = get_config(args.env)
    
    # 如果指定了自定义配置文件，加载它
    if args.config:
        custom_config = load_custom_config(args.config)
        if custom_config:
            # 合并自定义配置
            config.update(custom_config)
            logger.info(f"已加载自定义配置: {args.config}")
    
    # 应用命令行参数覆盖配置
    if args.iterations:
        config["max_iterations"] = args.iterations
    
    if args.delay:
        config["iteration_delay"] = args.delay
    
    if args.log_level:
        config["log_level"] = args.log_level
    
    if args.api_key:
        config["api_key"] = args.api_key
    
    if args.base_url:
        config["base_url"] = args.base_url
    
    # 设置日志系统
    setup_logger(config)
    
    # 检查API密钥
    if not config.get("api_key") or config.get("api_key") == "your_api_key_here":
        logger.error("未设置API密钥！请在配置文件中设置或使用 --api-key 参数提供")
        sys.exit(1)
    
    # 获取任务描述
    task = args.task
    if not task:
        task = safe_get_task_from_input()
        if not task:
            logger.error("未提供任务描述")
            sys.exit(1)
    
    # 输出启动信息
    logger.info("=" * 50)
    logger.info("AI-UI-Controller 启动")
    logger.info(f"环境: {args.env}")
    logger.info(f"任务: {task}")
    logger.info(f"最大迭代次数: {config['max_iterations']}")
    logger.info(f"迭代延迟: {config['iteration_delay']}秒")
    logger.info("=" * 50)
    
    # 创建UI代理
    agent = UIAgent(config)
    
    # 如果请求列出提示词，则显示并退出
    if args.list_prompts:
        prompts = agent.brain.list_prompts()
        print("\n可用提示词列表:")
        for i, prompt_name in enumerate(prompts):
            current = " (当前)" if prompt_name == agent.brain.prompt_manager.current_prompt else ""
            print(f"{i+1}. {prompt_name}{current}")
        print()
        return 0

    # 设置提示词
    context = {"task": task}
    
    if args.prompt:
        # 检查是文件路径还是提示词名称
        if os.path.exists(args.prompt):
            # 从文件加载提示词
            try:
                with open(args.prompt, 'r', encoding='utf-8') as f:
                    prompt_content = f.read()
                    
                # 使用文件名作为提示词名称
                prompt_name = os.path.splitext(os.path.basename(args.prompt))[0]
                
                # 添加提示词并设置为当前提示词
                agent.brain.add_prompt(prompt_name, prompt_content)
                agent.brain.set_prompt(prompt_name, context)
                
                logger.info(f"已从文件加载提示词: {args.prompt}")
            except Exception as e:
                logger.error(f"加载提示词文件出错: {e}")
        else:
            # 使用指定的提示词名称
            if not agent.brain.set_prompt(args.prompt, context):
                logger.warning(f"提示词'{args.prompt}'不存在，使用默认提示词")
    
    try:
        # 执行任务
        logger.info("开始执行任务...")
        start_time = time.time()
        result = agent.run(task)
        elapsed = time.time() - start_time
        
        # 输出结果摘要
        logger.info("=" * 50)
        logger.info(f"任务执行完成，总用时: {elapsed:.2f}秒")
        logger.info(f"总迭代次数: {result['iterations']}")
        
        # 如果有历史记录，输出操作统计
        history = result.get("history", [])
        if history:
            success_count = sum(1 for item in history if item.get("result", {}).get("success", False))
            fail_count = len(history) - success_count
            logger.info(f"操作总数: {len(history)}, 成功: {success_count}, 失败: {fail_count}")
        
        logger.info("=" * 50)
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("任务被用户中断")
        return 130  # SIGINT的标准退出码
    
    except Exception as e:
        logger.error(f"任务执行出错: {e}")
        logger.debug(f"错误详情: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)