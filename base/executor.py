from abc import ABC, abstractmethod
from loguru import logger

class BaseExecutor(ABC):
    """执行器基类，定义执行动作的接口"""
    
    def __init__(self, config):
        """初始化执行器
        
        Args:
            config (dict): 配置参数
        """
        self.config = config
        logger.debug("Executor module initialized")
    
    @abstractmethod
    def execute(self, action):
        """执行指定的动作
        
        Args:
            action (dict): 动作描述，包含类型和参数
            
        Returns:
            bool: 执行是否成功
        """
        pass
    
    @abstractmethod
    def validate(self, action):
        """验证动作是否有效
        
        Args:
            action (dict): 动作描述
            
        Returns:
            bool: 动作是否有效
        """
        pass