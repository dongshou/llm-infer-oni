from abc import ABC, abstractmethod
from loguru import logger

class BaseAgent(ABC):
    """代理基类，定义代理的基本接口和生命周期方法"""
    
    def __init__(self, config):
        """初始化代理
        
        Args:
            config (dict): 配置参数
        """
        self.config = config
        self.running = False
        logger.info("Agent initialized with config")
    
    @abstractmethod
    def setup(self):
        """设置代理，初始化所需组件"""
        pass
    
    @abstractmethod
    def setup_middlewares(self):
        """设置和初始化中间件"""
        pass
    
    @abstractmethod
    def run(self, task):
        """执行指定任务的主循环
        
        Args:
            task (str): 任务描述
        """
        pass
    
    @abstractmethod
    def step(self):
        """执行单个步骤的循环
        
        Returns:
            bool: 如果需要停止循环则返回True，否则返回False
        """
        pass
    
    @abstractmethod
    def stop(self):
        """停止代理执行"""
        pass