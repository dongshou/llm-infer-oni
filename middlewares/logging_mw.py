"""
日志记录中间件 - 记录系统操作流程的详细日志（支持action为list类型）
"""

import json
import time
from loguru import logger
from base.middleware import Middleware
from typing import Union, List, Dict, Any

class LoggingMiddleware(Middleware):
    """日志记录中间件，记录系统操作的详细日志（支持单动作和动作列表）"""
    
    def __init__(self, config=None):
        """初始化日志中间件
        
        Args:
            config (dict, optional): 配置参数
        """
        super().__init__(config)
        self.log_level = self.config.get("log_level", "INFO")
        self.log_details = self.config.get("log_details", True)
        self.log_state = self.config.get("log_state", False)
        self.operation_counter = 0
        
        logger.info("日志中间件初始化完成，日志级别: {}", self.log_level)
    
    def _log_action(self, action: Dict[str, Any]) -> str:
        """统一处理单个动作的日志记录"""
        action_type = action.get("type", "unknown")
        
        if action_type == "move":
            return f"移动鼠标到 ({action.get('x', 0)}, {action.get('y', 0)})"
        elif action_type == "click":
            return f"点击鼠标 {action.get('button', 'left')} 在 ({action.get('x', 0)}, {action.get('y', 0)})"
        elif action_type == "type":
            text = action.get("text", "")
            display_text = text if len(text) < 20 else f"{text[:17]}..."
            return f"输入文本 '{display_text}'"
        elif action_type == "key":
            keys = action.get("keys", [])
            keys = [keys] if isinstance(keys, str) else keys
            return f"按键 {'+'.join(keys)}"
        elif action_type == "scroll":
            return f"滚动 {action.get('direction', 'down')} {action.get('clicks', 1)} 次"
        elif action_type == "stop":
            return f"停止，原因: {action.get('reason', '未指定')}"
        else:
            return f"未知动作类型 {action_type}"

    def process_before_perception(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """感知前记录"""
        self.operation_counter += 1
        iteration = context.get("iteration", 0)
        
        logger.debug("===== 操作 #{} (迭代 {}) 开始 =====", 
                   self.operation_counter, iteration)
        
        context["_logging"] = context.get("_logging", {})
        context["_logging"]["start_time"] = time.time()
        return context
    
    def process_after_perception(self, state: Dict[str, Any], context: Dict[str, Any]) -> tuple:
        """感知后记录"""
        if state:
            screen_info = {
                "width": state.get("screen_width", 0),
                "height": state.get("screen_height", 0),
                "cursor": state.get("cursor_position", (0, 0))
            }
            
            logger.debug("屏幕状态: {}x{}, 鼠标位置: {}", 
                       screen_info["width"], screen_info["height"], 
                       screen_info["cursor"])
            
            if self.log_state and "image" in state:
                image_length = len(state["image"]) if state["image"] else 0
                logger.debug("屏幕图像数据大小: {} 字节", image_length)
        else:
            logger.warning("屏幕状态获取失败")
        
        return state, context
    
    def process_before_decision(self, state: Dict[str, Any], context: Dict[str, Any]) -> tuple:
        """决策前记录"""
        logger.debug("开始进行决策")
        return state, context
    
    def process_after_decision(self, 
                             action: Union[Dict[str, Any], List[Dict[str, Any]]], 
                             state: Dict[str, Any], 
                             context: Dict[str, Any]) -> tuple:
        """决策后记录（支持单动作和动作列表）"""
        if not action:
            logger.warning("决策失败，未产生有效动作")
            return action, state, context
            
        if isinstance(action, list):
            logger.info("决策: 批量动作 (共 {} 个)", len(action))
            for i, act in enumerate(action, 1):
                logger.info("  {}. {}", i, self._log_action(act))
                if self.log_details:
                    logger.debug("  动作详情: {}", json.dumps(act, ensure_ascii=False))
        else:
            logger.info("决策: {}", self._log_action(action))
            if self.log_details:
                logger.debug("决策详情: {}", json.dumps(action, ensure_ascii=False))
                
        return action, state, context
    
    def process_before_execution(self, 
                               action: Union[Dict[str, Any], List[Dict[str, Any]]], 
                               context: Dict[str, Any]) -> tuple:
        """执行前记录（支持单动作和动作列表）"""
        if action:
            if isinstance(action, list):
                logger.debug("准备执行批量动作 (共 {} 个)", len(action))
            else:
                logger.debug("准备执行动作: {}", action.get("type", "unknown"))
            
            if "_logging" in context:
                context["_logging"]["execute_start_time"] = time.time()
                
        return action, context
    
    def process_after_execution(self, 
                              result: Union[Dict[str, Any], List[Dict[str, Any]]], 
                              action: Union[Dict[str, Any], List[Dict[str, Any]]], 
                              context: Dict[str, Any]) -> tuple:
        """执行后记录（支持单动作和动作列表的结果）"""
        if not result or not action:
            return result, action, context
            
        def _log_single_result(res: Dict[str, Any], act: Dict[str, Any]):
            success = res.get("success", False)
            action_type = act.get("type", "unknown")
            
            if success:
                logger.info("执行成功: {} 动作", action_type)
            else:
                logger.warning("执行失败: {} 动作, 原因: {}", 
                             action_type, res.get("error", "未知错误"))

        if isinstance(action, list):
            logger.info("批量执行结果 (共 {} 个动作)", len(action))
            for i, (res, act) in enumerate(zip(result, action), 1):
                logger.info("  {}. 动作结果:", i)
                _log_single_result(res, act)
        else:
            _log_single_result(result, action)
        
        # 计算总耗时
        if "_logging" in context and "start_time" in context["_logging"]:
            total_time = time.time() - context["_logging"]["start_time"]
            logger.debug("===== 操作 #{} 完成，总耗时: {:.2f}秒 =====", 
                       self.operation_counter, total_time)
                
        return result, action, context