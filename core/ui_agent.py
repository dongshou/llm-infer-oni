"""
主代理模块 - 协调系统各组件的工作
"""

import time
import traceback
from loguru import logger
from base.agent import BaseAgent
from core.screen_capture import ScreenCapture
from core.input_controller import InputController
from core.llm_decision import LLMDecision
from base.middleware import MiddlewareManager

class UIAgent(BaseAgent):
    """UI代理实现，控制整个系统流程"""
    
    def __init__(self, config):
        """初始化UI代理
        
        Args:
            config (dict): 配置参数
        """
        super().__init__(config)
        # 设置运行参数
        self.max_iterations = config.get("max_iterations", 100)
        self.iteration_delay = config.get("iteration_delay", 0.5)
        logger.info("UI代理初始化完成，最大迭代次数={}，迭代延迟={}秒", 
                  self.max_iterations, self.iteration_delay)
    
    def setup(self):
        """设置代理所需的组件"""
        # 初始化组件
        logger.info("正在设置UI代理组件")
        self.perception = ScreenCapture(self.config)
        self.executor = InputController(self.config)
        self.brain = LLMDecision(self.config)
        
        # 初始化上下文
        self.context = {
            "history": [],
            "start_time": time.time(),
            "iteration": 0,
            # 设置默认提示词
            "prompt_name": self.config.get("default_prompt_name", "default")
        }
        
        logger.info("UI代理组件初始化完成")
    
    def setup_middlewares(self):
        """设置中间件"""
        logger.info("正在设置UI代理中间件")
        self.middleware_manager = MiddlewareManager()
        
        # 添加配置的中间件
        middleware_configs = self.config.get("middlewares", [])
        for middleware_class in middleware_configs:
            try:
                # 导入并实例化中间件
                module_path, class_name = middleware_class.rsplit(".", 1)
                module = __import__(module_path, fromlist=[class_name])
                middleware = getattr(module, class_name)(self.config)
                self.middleware_manager.add(middleware)
            except Exception as e:
                logger.error("加载中间件{}失败: {}", middleware_class, e)
        
        logger.info("UI代理中间件初始化完成")
    
    def run(self, task):
        """执行指定任务的主循环
        
        Args:
            task (str): 任务描述
        """
        
        # 设置组件和中间件
        self.setup()
        self.setup_middlewares()
        
        # 设置任务
        self.context["task"] = task
        self.running = True
        
        # 根据任务自动选择提示词（如果启用）
        if self.config.get("auto_prompt", True) and "prompt_name" not in self.context:
            self._auto_select_prompt(task)
            
        logger.info("开始执行UI代理任务: '{}'", task)
        logger.info("使用提示词: {}", self.context.get("prompt_name", "default"))

        
        # 初始化计数器和时间
        iteration = 0
        start_time = time.time()
        self.context["start_time"] = start_time
        
        # 主循环
        try:
            while self.running:
                # 更新迭代计数和时间
                iteration += 1
                self.context["iteration"] = iteration
                self.context["current_time"] = time.time()
                
                logger.info("迭代 {}/{}", iteration, self.max_iterations)
                
                # 执行单步操作
                stop = self.step()
                
                # 是否需要停止
                if stop:
                    logger.info("停止: 收到停止信号")
                    break
                
                # 检查迭代次数限制
                if iteration >= self.max_iterations:
                    logger.info("停止: 达到最大迭代次数")
                    break
                
                # 迭代间延迟
                if self.iteration_delay > 0:
                    time.sleep(self.iteration_delay)
                
        except KeyboardInterrupt:
            logger.info("UI代理被用户中断")
        except Exception as e:
            logger.exception("UI代理主循环出错: {}", e)
        finally:
            self.stop()
            
        # 计算执行时间
        elapsed = time.time() - start_time
        logger.info("UI代理在{}次迭代后完成，用时{:.2f}秒", iteration, elapsed)
        
        return {
            "iterations": iteration,
            "elapsed_time": elapsed,
            "task": task,
            "history": self.context.get("history", [])
        }
        
    def _auto_select_prompt(self, task):
        """根据任务内容自动选择最合适的提示词
        
        Args:
            task (str): 任务描述
        
        Returns:
            bool: 是否成功选择提示词
        """
        task_lower = task.lower()
        mapping = self.config.get("task_prompt_mapping", {})
        
        for prompt_name, keywords in mapping.items():
            for keyword in keywords:
                if keyword.lower() in task_lower:
                    success = self.brain.set_prompt(prompt_name, self.context)
                    if success:
                        logger.info("根据任务内容自动选择提示词: {}", prompt_name)
                        return True
        
        # 如果没有匹配的提示词，使用默认提示词
        default_name = self.config.get("default_prompt_name", "default")
        success = self.brain.set_prompt(default_name, self.context)
        if success:
            logger.info("未找到匹配的提示词，使用默认提示词: {}", default_name)
        
        return success
    
    def step(self):
        """执行单个步骤的循环
        
        Returns:
            bool: 如果需要停止循环则返回True，否则返回False
        """
        step_start = time.time()
        logger.debug("开始执行步骤")
        
        try:
            # 1. 中间件处理：感知前
            self.context = self.middleware_manager.process_before_perception(self.context)
            
            # 2. 获取屏幕状态
            logger.debug("正在捕获屏幕")
            state = self.perception.process()
            
            # 3. 中间件处理：感知后
            state, self.context = self.middleware_manager.process_after_perception(state, self.context)
            
            # 4. 中间件处理：决策前
            state, self.context = self.middleware_manager.process_before_decision(state, self.context)
            
            # 5. 决策下一步操作
            logger.debug("正在进行决策")
            action = self.brain.decide(state, self.context)
            logger.info("决策结果: {}", action)
            
            # 处理 action 可能是 list 的情况
            actions = action if isinstance(action, list) else [action]
            
            # 用于记录最终结果
            final_result = False
            
            for act in actions:
                current_action = act  # 当前处理的action
                
                try:
                    # 6. 中间件处理：决策后
                    current_action, state, self.context = self.middleware_manager.process_after_decision(
                        current_action, state, self.context)
                    
                    # 检查动作是否被拒绝
                    if current_action is None:
                        logger.warning("动作被中间件拒绝")
                        continue
                    
                    # 检查是否需要停止
                    if should_stop(current_action):
                        logger.info("收到停止动作: {}", current_action.get("reason", "未指定原因"))
                        
                        # 记录执行结果
                        result = {
                            "success": True,
                            "timestamp": time.time(),
                            "message": current_action.get("reason", "任务完成")
                        }
                        
                        # 中间件处理：执行后
                        result, current_action, self.context = self.middleware_manager.process_after_execution(
                            result, current_action, self.context)
                        
                        # 更新历史记录
                        history_item = {
                            "action": current_action,
                            "result": result,
                            "timestamp": result["timestamp"]
                        }
                        self.context["history"].append(history_item)
                        
                        return True  # 立即停止整个循环
                    
                    # 7. 中间件处理：执行前
                    current_action, self.context = self.middleware_manager.process_before_execution(
                        current_action, self.context)
                    
                    # 检查动作是否被拒绝
                    if current_action is None:
                        logger.warning("动作在执行前被中间件拒绝")
                        continue
                    
                    # 8. 执行动作
                    logger.debug("正在执行动作")
                    success = self.executor.execute(current_action)
                    
                    # 9. 记录执行结果
                    result = {
                        "success": success,
                        "timestamp": time.time(),
                        "error": None if success else "执行失败"
                    }
                    
                    # 10. 中间件处理：执行后
                    result, current_action, self.context = self.middleware_manager.process_after_execution(
                        result, current_action, self.context)
                    
                    # 11. 更新历史记录
                    history_item = {
                        "action": current_action,
                        "result": result,
                        "timestamp": result["timestamp"]
                    }
                    self.context["history"].append(history_item)
                    
                    # 如果任何一个动作执行成功，则标记为成功
                    if success:
                        final_result = True
                        
                except Exception as e:
                    logger.exception("处理单个动作时出错: {}", e)
                    logger.debug("错误堆栈: {}", traceback.format_exc())
                    continue
            
            # 记录步骤执行时间
            step_elapsed = time.time() - step_start
            logger.debug("步骤执行完成，耗时: {:.2f}秒", step_elapsed)
            
            # 如果有任何一个动作要求停止，则返回True
            return final_result
            
        except Exception as e:
            logger.exception("步骤执行出错: {}", e)
            logger.debug("错误堆栈: {}", traceback.format_exc())
            return False
        
    def stop(self):
        """停止代理执行"""
        self.running = False
        logger.info("UI代理已停止")


# 检查是否需要停止
def should_stop(action):
    # 处理字典情况
    if isinstance(action, dict):
        if action.get("type") == "stop":
            stop_reason = action.get("reason", "未指定原因")
            logger.info(f"收到停止动作(字典)，原因: {stop_reason}")
            return True
    
    # 处理列表情况
    elif isinstance(action, list):
        for item in action:
            if isinstance(item, dict) and item.get("type") == "stop":
                stop_reason = item.get("reason", "未指定原因")
                logger.info(f"收到停止动作(列表中的元素)，原因: {stop_reason}")
                return True
    
    # 其他情况
    return False