from abc import ABC, abstractmethod
from loguru import logger

class Middleware(ABC):
    """中间件基类，定义中间件的接口"""
    
    def __init__(self, config=None):
        """初始化中间件
        
        Args:
            config (dict, optional): 配置参数
        """
        self.config = config or {}
        logger.debug("{} middleware initialized", self.__class__.__name__)
    
    def process_before_perception(self, context):
        """感知前处理
        
        Args:
            context (dict): 当前上下文
            
        Returns:
            dict: 处理后的上下文
        """
        return context
    
    def process_after_perception(self, state, context):
        """感知后处理
        
        Args:
            state (dict): 感知结果
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的状态, 处理后的上下文)
        """
        return state, context
    
    def process_before_decision(self, state, context):
        """决策前处理
        
        Args:
            state (dict): 当前状态
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的状态, 处理后的上下文)
        """
        return state, context
    
    def process_after_decision(self, action, state, context):
        """决策后处理
        
        Args:
            action (dict): 决策结果
            state (dict): 当前状态
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的动作, 处理后的状态, 处理后的上下文)
        """
        return action, state, context
    
    def process_before_execution(self, action, context):
        """执行前处理
        
        Args:
            action (dict): 将要执行的动作
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的动作, 处理后的上下文)
        """
        return action, context
    
    def process_after_execution(self, result, action, context):
        """执行后处理
        
        Args:
            result (dict): 执行结果
            action (dict): 执行的动作
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的结果, 处理后的动作, 处理后的上下文)
        """
        return result, action, context


class MiddlewareManager:
    """中间件管理器，负责管理和调用中间件链"""
    
    def __init__(self):
        """初始化中间件管理器"""
        self.middlewares = []
        logger.debug("Middleware manager initialized")
    
    def add(self, middleware):
        """添加中间件到链中
        
        Args:
            middleware (Middleware): 中间件实例
            
        Returns:
            MiddlewareManager: 返回自身以支持链式调用
        """
        if not isinstance(middleware, Middleware):
            raise TypeError("Middleware must be an instance of Middleware base class")
        
        self.middlewares.append(middleware)
        logger.debug("Added middleware: {}", middleware.__class__.__name__)
        return self
    
    def remove(self, middleware_class):
        """移除特定类型的中间件
        
        Args:
            middleware_class (class): 中间件类
            
        Returns:
            MiddlewareManager: 返回自身以支持链式调用
        """
        initial_count = len(self.middlewares)
        self.middlewares = [m for m in self.middlewares if not isinstance(m, middleware_class)]
        
        if len(self.middlewares) < initial_count:
            logger.debug("Removed middleware: {}", middleware_class.__name__)
        
        return self
    
    def process_before_perception(self, context):
        """调用所有中间件的感知前处理
        
        Args:
            context (dict): 当前上下文
            
        Returns:
            dict: 处理后的上下文
        """
        for middleware in self.middlewares:
            try:
                context = middleware.process_before_perception(context)
            except Exception as e:
                logger.error("Error in middleware {} process_before_perception: {}", 
                             middleware.__class__.__name__, e)
        return context
    
    def process_after_perception(self, state, context):
        """调用所有中间件的感知后处理
        
        Args:
            state (dict): 感知结果
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的状态, 处理后的上下文)
        """
        for middleware in self.middlewares:
            try:
                state, context = middleware.process_after_perception(state, context)
            except Exception as e:
                logger.error("Error in middleware {} process_after_perception: {}", 
                             middleware.__class__.__name__, e)
        return state, context
    
    def process_before_decision(self, state, context):
        """调用所有中间件的决策前处理
        
        Args:
            state (dict): 当前状态
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的状态, 处理后的上下文)
        """
        for middleware in self.middlewares:
            try:
                state, context = middleware.process_before_decision(state, context)
            except Exception as e:
                logger.error("Error in middleware {} process_before_decision: {}", 
                             middleware.__class__.__name__, e)
        return state, context
    
    def process_after_decision(self, action, state, context):
        """调用所有中间件的决策后处理
        
        Args:
            action (dict): 决策结果
            state (dict): 当前状态
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的动作, 处理后的状态, 处理后的上下文)
        """
        for middleware in self.middlewares:
            try:
                action, state, context = middleware.process_after_decision(action, state, context)
                # 如果中间件返回None作为动作，表示动作被拒绝
                if action is None:
                    logger.warning("Action rejected by middleware: {}", middleware.__class__.__name__)
                    break
            except Exception as e:
                logger.error("Error in middleware {} process_after_decision: {}", 
                             middleware.__class__.__name__, e)
        return action, state, context
    
    def process_before_execution(self, action, context):
        """调用所有中间件的执行前处理
        
        Args:
            action (dict): 将要执行的动作
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的动作, 处理后的上下文)
        """
        for middleware in self.middlewares:
            try:
                action, context = middleware.process_before_execution(action, context)
                # 如果中间件返回None作为动作，表示动作被拒绝
                if action is None:
                    logger.warning("Action rejected by middleware: {}", middleware.__class__.__name__)
                    break
            except Exception as e:
                logger.error("Error in middleware {} process_before_execution: {}", 
                             middleware.__class__.__name__, e)
        return action, context
    
    def process_after_execution(self, result, action, context):
        """调用所有中间件的执行后处理
        
        Args:
            result (dict): 执行结果
            action (dict): 执行的动作
            context (dict): 当前上下文
            
        Returns:
            tuple: (处理后的结果, 处理后的动作, 处理后的上下文)
        """
        for middleware in self.middlewares:
            try:
                result, action, context = middleware.process_after_execution(result, action, context)
            except Exception as e:
                logger.error("Error in middleware {} process_after_execution: {}", 
                             middleware.__class__.__name__, e)
        return result, action, context