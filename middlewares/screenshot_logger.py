"""
截图记录中间件 - 保存屏幕截图和对应的模型执行操作（支持动作列表）
"""

import os
import time
import json
import base64
from datetime import datetime
from pathlib import Path
import uuid
from PIL import Image
import io
import re
from typing import Union, List, Dict, Any
from loguru import logger
from base.middleware import Middleware

class ScreenshotLoggerMiddleware(Middleware):
    """截图记录中间件，用于记录每次操作的屏幕截图和对应的操作（支持单个动作或动作列表）"""
    
    def __init__(self, config=None):
        """初始化截图记录中间件
        
        Args:
            config (dict, optional): 配置参数
        """
        super().__init__(config)
        
        # 获取配置
        self.config = config or {}
        self.enabled = self.config.get("screenshot_logger_enabled", True)
        
        # 设置存储目录
        base_dir = self.config.get("screenshot_log_dir", "logs/screenshots")
        self.log_dir = os.path.join(base_dir, datetime.now().strftime("%Y%m%d_%H%M%S"))
        
        # 设置记录频率
        self.log_every_n_steps = self.config.get("screenshot_log_frequency", 1)
        
        # 是否同时保存原始图像
        self.save_raw_image = self.config.get("screenshot_save_raw", True)
        
        # 是否保存base64编码的图像数据
        self.save_base64 = self.config.get("screenshot_save_base64", False)
        
        # 当前步骤计数
        self.step_counter = 0
        
        # 会话ID，用于关联同一次运行中的所有记录
        self.session_id = str(uuid.uuid4())[:8]
        
        # 确保目录存在
        if self.enabled:
            self._ensure_dirs()
            
            # 创建操作日志文件
            self.actions_log_path = os.path.join(self.log_dir, "actions.jsonl")
            
            logger.info("截图记录中间件初始化完成，记录目录: {}", self.log_dir)
    
    def _ensure_dirs(self):
        """确保所需目录存在"""
        os.makedirs(self.log_dir, exist_ok=True)
        logger.debug("创建截图记录目录: {}", self.log_dir)
    
    def _is_stop_action(self, action: Union[Dict, List]) -> bool:
        """检查是否为停止动作"""
        if isinstance(action, dict):
            return action.get("type") == "stop"
        elif isinstance(action, list):
            return any(self._is_stop_action(a) for a in action if isinstance(a, dict))
        return False
    
    def _log_single_action(self, action: Dict, state: Dict, context: Dict):
        """记录单个动作到日志"""
        if not isinstance(action, dict):
            return
        
        # 获取当前图像路径和时间戳
        image_path = context.get("_current_image_path")
        step_time = context.get("_current_step_time", time.time())
        iteration = context.get("iteration", 0)
        
        try:
            # 从上下文中提取模型的完整回复（如果有）
            full_response = context.get("_full_model_response", "")
            
            # 保存模型分析文本到单独文件
            if full_response:
                analysis_path = os.path.join(self.log_dir, f"step_{iteration:04d}_{int(step_time)}_analysis.txt")
                with open(analysis_path, "w", encoding="utf-8") as f:
                    f.write(full_response)
                logger.debug("模型分析已保存: {}", analysis_path)
            
            # 准备记录数据
            log_entry = {
                "session_id": self.session_id,
                "iteration": iteration,
                "timestamp": step_time,
                "image_path": os.path.basename(image_path) if image_path else None,
                "action": action,
                "task": context.get("task", ""),
                "prompt_name": context.get("prompt_name", "default")
            }
            
            # 添加模型分析概要
            if full_response:
                json_match = re.search(r'{.*}', full_response, re.DOTALL)
                if json_match:
                    analysis_text = full_response[:json_match.start()].strip()
                else:
                    analysis_text = full_response
                
                # 截断过长的分析文本
                max_length = 1000
                log_entry["model_analysis"] = analysis_text[:max_length] + "..." if len(analysis_text) > max_length else analysis_text
            
            # 添加Base64图像数据（如果需要）
            if self.save_base64 and "image" in state:
                base64_data = state["image"]
                max_length = 1000
                log_entry["image_base64_preview"] = base64_data[:max_length] + "..." if len(base64_data) > max_length else base64_data
            
            # 将动作信息写入日志文件
            with open(self.actions_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
            logger.debug("动作已记录到日志: {}", action.get("type", "unknown"))
            
            # 记录模型分析到系统日志
            if full_response:
                analysis_lines = [line.strip() for line in analysis_text.split('\n') if line.strip()]
                for i, line in enumerate(analysis_lines[:5]):
                    prefix = "模型分析: " if i == 0 else "         "
                    logger.info("{}{}", prefix, line[:100] + ("..." if len(line) > 100 else ""))
                if len(analysis_lines) > 5:
                    logger.info("         ... (更多分析内容已保存到文件)")
        except Exception as e:
            logger.error("记录动作日志失败: {}", e)
    
    def process_after_perception(self, state: Dict, context: Dict) -> tuple:
        """感知后处理：记录当前状态的原始截图"""
        if not self.enabled:
            return state, context
        
        self.step_counter += 1
        
        if self.step_counter % self.log_every_n_steps != 0:
            return state, context
        
        if self.save_raw_image and "image" in state:
            try:
                timestamp = time.time()
                iteration = context.get("iteration", 0)
                file_name = f"step_{iteration:04d}_{int(timestamp)}_before.png"
                file_path = os.path.join(self.log_dir, file_name)
                
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(state["image"]))
                
                context["_current_image_path"] = file_path
                context["_current_step_time"] = timestamp
                
                logger.debug("截图已保存: {}", file_path)
            except Exception as e:
                logger.error("保存截图失败: {}", e)
        
        return state, context
    
    def process_after_decision(self, action: Union[Dict, List], state: Dict, context: Dict) -> tuple:
        """决策后处理：记录决策结果（支持单个动作或动作列表）"""
        if not self.enabled or action is None:
            return action, state, context
        
        if self.step_counter % self.log_every_n_steps != 0:
            return action, state, context
        
        # 如果是停止动作，不记录
        if self._is_stop_action(action):
            return action, state, context
        
        # 处理动作列表
        if isinstance(action, list):
            for act in action:
                if isinstance(act, dict) and not self._is_stop_action(act):
                    self._log_single_action(act, state, context)
        # 处理单个动作
        elif isinstance(action, dict):
            self._log_single_action(action, state, context)
        
        return action, state, context
    
    def process_after_execution(self, result: Dict, action: Union[Dict, List], context: Dict) -> tuple:
        """执行后处理：记录执行结果"""
        if not self.enabled or action is None:
            return result, action, context
        
        if self.step_counter % self.log_every_n_steps != 0:
            return result, action, context
        
        image_path = context.get("_current_image_path")
        
        if image_path and result:
            try:
                base_path = os.path.splitext(image_path)[0]
                result_path = f"{base_path}_result.json"
                
                result_data = {
                    "session_id": self.session_id,
                    "image_path": os.path.basename(image_path),
                    "action": action,
                    "result": result,
                    "timestamp": time.time(),
                    "success": result.get("success", False)
                }
                
                with open(result_path, "w", encoding="utf-8") as f:
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                
                context.pop("_current_image_path", None)
                context.pop("_current_step_time", None)
                
                logger.debug("执行结果已记录: {}", result_path)
            except Exception as e:
                logger.error("记录执行结果失败: {}", e)
        
        return result, action, context
    
    def generate_report(self) -> str:
        """生成操作记录报告"""
        if not self.enabled:
            return None
        
        try:
            report_path = os.path.join(self.log_dir, "report.html")
            actions = []
            
            if os.path.exists(self.actions_log_path):
                with open(self.actions_log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            actions.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>AI操作记录报告</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .header {{ background-color: #f0f0f0; padding: 10px; margin-bottom: 20px; }}
                        .action-card {{ border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; border-radius: 5px; }}
                        .action-card img {{ max-width: 100%; max-height: 300px; }}
                        .tabs {{ display: flex; margin-bottom: 0; }}
                        .tab {{ padding: 10px 15px; cursor: pointer; background-color: #eee; border-radius: 5px 5px 0 0; margin-right: 5px; }}
                        .tab.active {{ background-color: #f8f8f8; }}
                        .tab-content {{ display: none; }}
                        .tab-content.active {{ display: block; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>AI操作记录报告</h1>
                        <p>会话ID: {self.session_id}</p>
                        <p>记录时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                        <p>总操作数: {len(actions)}</p>
                    </div>
                """)
                
                for i, action_data in enumerate(actions):
                    f.write(f"""
                    <div class="action-card">
                        <h2>步骤 {i+1}: {action_data.get('action', {}).get('type', 'unknown')}</h2>
                        <p>时间: {datetime.fromtimestamp(action_data.get('timestamp', 0)).strftime('%H:%M:%S')}</p>
                        <img src="{action_data.get('image_path', '')}" alt="屏幕截图">
                        <pre>{json.dumps(action_data.get('action', {}), indent=2, ensure_ascii=False)}</pre>
                    </div>
                    """)
                
                f.write("</body></html>")
            
            logger.info("生成报告完成: {}", report_path)
            return report_path
        except Exception as e:
            logger.error("生成报告失败: {}", e)
            return None