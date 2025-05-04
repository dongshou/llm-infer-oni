"""
操作限流中间件 - 控制操作执行频率，防止操作过快（支持动作列表）
"""

import time
from typing import Union, List, Dict, Any
from loguru import logger
from base.middleware import Middleware

class ThrottlingMiddleware(Middleware):
    """操作限流中间件，防止操作执行过快（支持单个动作或动作列表）"""
    
    def __init__(self, config=None):
        """初始化限流中间件
        
        Args:
            config (dict, optional): 配置参数
        """
        super().__init__(config)
        self.last_action_time = 0
        
        # 默认延迟时间
        self.default_delay = self.config.get("action_delay", 1.0)
        
        # 不同动作类型的延迟设置
        self.action_delays = self.config.get("action_delays", {
            "move": 0.1,      # 移动鼠标的延迟较短
            "click": 0.1,     # 点击操作需要更长的延迟
            "type": 0.2,      # 文本输入的延迟
            "key": 0.1,       # 按键操作的延迟
            "scroll": 0.1,    # 滚动操作的延迟
            "composite": 0.1  # 复合动作的延迟
        })
        
        logger.info("限流中间件初始化完成，默认延迟: {}秒", self.default_delay)
    
    def _get_action_delay(self, action: Dict) -> float:
        """获取单个动作的延迟时间"""
        if not isinstance(action, dict):
            return 0.0
        
        action_type = action.get("type", "")
        
        # 复合动作的特殊处理
        if action_type == "composite" and "actions" in action:
            # 计算复合动作中所有子动作的最大延迟
            max_delay = 0.0
            for sub_action in action.get("actions", []):
                if isinstance(sub_action, dict):
                    max_delay = max(max_delay, self._get_action_delay(sub_action))
            return max(max_delay, self.action_delays.get("composite", self.default_delay))
        
        return self.action_delays.get(action_type, self.default_delay)
    
    def _get_max_delay(self, action: Union[Dict, List]) -> float:
        """获取动作或动作列表的最大延迟时间"""
        if isinstance(action, list):
            max_delay = 0.0
            for act in action:
                if isinstance(act, dict):
                    max_delay = max(max_delay, self._get_action_delay(act))
            return max_delay
        elif isinstance(action, dict):
            return self._get_action_delay(action)
        return 0.0
    
    def process_before_execution(self, action: Union[Dict, List], context: Dict) -> tuple:
        """执行前检查时间间隔，必要时添加延迟（支持单个动作或动作列表）
        
        Args:
            action (dict|list): 将要执行的动作
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的动作, 处理后的上下文)
        """
        if action is None:
            return action, context
        
        current_time = time.time()
        
        # 获取这个动作或动作列表的最大延迟设置
        delay = self._get_max_delay(action)
        
        # 计算需要等待的时间
        elapsed = current_time - self.last_action_time
        wait_time = max(0, delay - elapsed)
        
        if wait_time > 0:
            action_type = action.get("type", "multiple") if isinstance(action, dict) else "multiple"
            logger.debug("限流: 在执行{}动作前等待{:.2f}秒", 
                      action_type, wait_time)
            time.sleep(wait_time)
        
        return action, context
    
    def process_after_execution(self, result: Dict, action: Union[Dict, List], context: Dict) -> tuple:
        """执行后记录时间（支持单个动作或动作列表）
        
        Args:
            result (dict): 执行结果
            action (dict|list): 执行的动作
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的结果, 处理后的动作, 处理后的上下文)
        """
        # 更新最后动作执行时间
        self.last_action_time = time.time()
        
        # 记录执行情况
        if action is not None and context:
            action_type = action.get("type", "") if isinstance(action, dict) else "multiple"
            if action_type != "stop":
                elapsed_since_last = self.last_action_time - context.get("current_time", self.last_action_time)
                logger.debug("动作执行耗时: {:.2f}秒", elapsed_since_last)
        
        return result, action, context
    
    def reset_throttling(self):
        """重置限流计时器"""
        self.last_action_time = time.time()
        logger.debug("限流计时器已重置")