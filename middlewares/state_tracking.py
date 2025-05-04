"""
状态追踪中间件 - 维护操作历史和状态信息（支持动作列表）
"""

import time
import copy
from typing import Union, List, Dict, Any
from loguru import logger
from base.middleware import Middleware

class StateTrackingMiddleware(Middleware):
    """状态追踪中间件，维护操作历史和状态信息（支持单个动作或动作列表）"""
    
    def __init__(self, config=None):
        """初始化状态追踪中间件
        
        Args:
            config (dict, optional): 配置参数
        """
        super().__init__(config)
        self.max_history = self.config.get("max_history", 10)
        self.track_stats = self.config.get("track_stats", True)
        self.track_duration = self.config.get("track_duration", True)
        
        # 统计信息
        self.stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "action_types": {},
            "start_time": time.time(),
            "runtime": 0.0
        }
        
        logger.info("状态追踪中间件初始化完成，最大历史记录数: {}", self.max_history)
    
    def _update_stats(self, action: Dict, result: Dict):
        """更新统计信息"""
        if not self.track_stats or not action:
            return
        
        action_type = action.get("type", "unknown")
        success = result.get("success", False) if result else False
        
        # 更新基本计数
        self.stats["total_actions"] += 1
        if success:
            self.stats["successful_actions"] += 1
        else:
            self.stats["failed_actions"] += 1
        
        # 更新动作类型统计
        if action_type not in self.stats["action_types"]:
            self.stats["action_types"][action_type] = {
                "total": 0, "success": 0, "fail": 0
            }
        
        self.stats["action_types"][action_type]["total"] += 1
        if success:
            self.stats["action_types"][action_type]["success"] += 1
        else:
            self.stats["action_types"][action_type]["fail"] += 1
        
        # 更新运行时间
        self.stats["runtime"] = time.time() - self.stats["start_time"]
    
    def process_before_perception(self, context: Dict) -> Dict:
        """感知前更新上下文
        
        Args:
            context (dict): 当前上下文
            
        Returns:
            dict: 处理后的上下文
        """
        # 初始化历史记录
        if "history" not in context:
            context["history"] = []
            
        # 添加当前时间戳
        context["current_time"] = time.time()
        
        # 如果启用了统计，添加到上下文
        if self.track_stats:
            context["stats"] = copy.deepcopy(self.stats)
            
        return context
    
    def process_after_decision(self, action: Union[Dict, List], state: Dict, context: Dict) -> tuple:
        """决策后记录当前动作到上下文（支持单个动作或动作列表）
        
        Args:
            action (dict|list): 决策结果
            state (dict): 当前状态
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的动作, 处理后的状态, 处理后的上下文)
        """
        if action is None:
            return action, state, context
        
        # 处理动作列表
        if isinstance(action, list):
            # 只记录第一个有效动作（或根据需求调整）
            for act in action:
                if isinstance(act, dict):
                    context["_current_action"] = {
                        "action": action,
                        "timestamp": context.get("current_time", time.time()),
                        "state_snapshot": {
                            "screen_width": state.get("screen_width", 0),
                            "screen_height": state.get("screen_height", 0),
                            "cursor_position": state.get("cursor_position", (0, 0))
                        } if state else None
                    }
                    # break
        
        if isinstance(action, dict):
            # 存储当前动作供执行后使用
            context["_current_action"] = {
                "action": action,
                "timestamp": context.get("current_time", time.time()),
                "state_snapshot": {
                    "screen_width": state.get("screen_width", 0),
                    "screen_height": state.get("screen_height", 0),
                    "cursor_position": state.get("cursor_position", (0, 0))
                } if state else None
            }
            
            # 如果启用了时长跟踪，记录开始时间
            if self.track_duration:
                context["_current_action"]["start_time"] = time.time()
        
        return action, state, context
    
    def process_after_execution(self, result: Dict, action: Union[Dict, List], context: Dict) -> tuple:
        """执行后更新历史记录（支持单个动作或动作列表）
        
        Args:
            result (dict): 执行结果
            action (dict|list): 执行的动作
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的结果, 处理后的动作, 处理后的上下文)
        """
        if action is None or "_current_action" not in context:
            return result, action, context
        
        # 获取当前动作记录
        action_record = context["_current_action"]
        
        # 添加执行结果
        action_record["result"] = result
        
        # 如果启用了时长跟踪，计算执行时长
        if self.track_duration and "start_time" in action_record:
            action_record["duration"] = time.time() - action_record["start_time"]
            del action_record["start_time"]  # 清理临时字段
        
        # 添加到历史记录
        if "history" in context:
            context["history"].append(action_record)
            
            # 限制历史记录长度
            if len(context["history"]) > self.max_history:
                context["history"] = context["history"][-self.max_history:]
        
        # 更新统计信息
        if isinstance(action, list):
            # 对于动作列表，更新所有有效动作的统计
            for act in action:
                if isinstance(act, dict):
                    self._update_stats(act, result)
        else:
            self._update_stats(action, result)
        
        # 清除临时存储
        del context["_current_action"]
        
        return result, action, context
    
    def get_success_rate(self) -> float:
        """获取操作成功率
        
        Returns:
            float: 操作成功率（0-1之间）
        """
        if self.stats["total_actions"] == 0:
            return 0.0
        
        return self.stats["successful_actions"] / self.stats["total_actions"]
    
    def get_action_stats(self, action_type: str = None) -> Dict:
        """获取指定动作类型的统计信息
        
        Args:
            action_type (str, optional): 动作类型，不指定则返回所有类型
            
        Returns:
            dict: 动作统计信息
        """
        if not action_type:
            return copy.deepcopy(self.stats["action_types"])
            
        return copy.deepcopy(self.stats["action_types"].get(action_type, {
            "total": 0, "success": 0, "fail": 0
        }))
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "total_actions": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "action_types": {},
            "start_time": time.time(),
            "runtime": 0.0
        }
        logger.debug("状态追踪统计信息已重置")