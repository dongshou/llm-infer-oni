from abc import ABC, abstractmethod
from loguru import logger

class BasePerception(ABC):
    """感知基类，定义获取和处理环境状态的接口"""
    
    def __init__(self, config):
        """初始化感知模块
        
        Args:
            config (dict): 配置参数
        """
        self.config = config
        logger.debug("Perception module initialized")
    
    @abstractmethod
    def capture(self):
        """捕获当前环境状态
        
        Returns:
            object: 捕获的原始状态数据
        """
        pass
    
    @abstractmethod
    def process(self):
        """处理捕获的状态数据，转换为适合决策使用的格式
        
        Returns:
            dict: 处理后的状态数据
        """
        pass