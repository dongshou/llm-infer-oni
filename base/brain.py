from abc import ABC, abstractmethod
from loguru import logger

class BaseBrain(ABC):
    """决策基类，定义决策逻辑的接口"""
    
    def __init__(self, config):
        """初始化决策模块
        
        Args:
            config (dict): 配置参数
        """
        self.config = config
        logger.debug("Brain module initialized")
    
    @abstractmethod
    def decide(self, state, context):
        """根据状态和上下文决定下一步动作
        
        Args:
            state (dict): 当前环境状态
            context (dict): 当前上下文，包含历史和任务信息
            
        Returns:
            dict: 下一步动作的描述
        """
        pass