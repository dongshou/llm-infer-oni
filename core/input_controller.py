"""
输入控制模块 - 负责执行鼠标和键盘操作
"""

import time
import pyautogui
from typing import List, Optional, Union, Tuple
from loguru import logger
from base.executor import BaseExecutor


class InputController(BaseExecutor):
    """应用程序输入控制模块"""
    
    def __init__(self, config):
        """初始化应用程序输入控制模块
        
        Args:
            config (dict): 配置参数
        """
        super().__init__(config)
        # 设置pyautogui安全设置
        pyautogui.FAILSAFE = True  # 移动鼠标到屏幕角落可以中断
        pyautogui.PAUSE = config.get("pyautogui_pause", 0.1)  # 操作间隔时间
        
        # 鼠标移动的持续时间
        self.move_duration = config.get("move_duration", 0.5)
        # 键盘输入的间隔时间
        self.type_interval = config.get("type_interval", 0.1)
        
        logger.debug("Input controller initialized, move_duration={}, type_interval={}", 
                    self.move_duration, self.type_interval)

    def validate(self, action):
        """验证动作是否有效
        
        Args:
            action (dict): 动作描述
            
        Returns:
            bool: 动作是否有效
        """
        if not isinstance(action, dict):
            logger.error("Invalid action: not a dictionary")
            return False
        
        # 检查动作类型
        action_type = action.get("type")
        if not action_type:
            logger.error("Invalid action: missing type")
            return False
        
        # 根据不同的动作类型验证参数
        if action_type == "move":
            # 移动动作需要x和y坐标
            if "x" not in action or "y" not in action:
                logger.error("Invalid move action: missing coordinates")
                return False
        
        elif action_type == "click":
            # 点击动作需要坐标（除非是在当前位置点击）
            if action.get("x") is not None and action.get("y") is not None:
                pass  # 坐标存在，有效
            elif action.get("x") is None and action.get("y") is None:
                pass  # 坐标都不存在，在当前位置点击，有效
            else:
                logger.error("Invalid click action: must provide both x and y or neither")
                return False
        
        elif action_type == "type":
            # 输入动作需要text内容
            if "text" not in action:
                logger.error("Invalid type action: missing text")
                return False
        
        elif action_type == "key":
            # 按键动作需要keys列表或单个键
            if "keys" not in action:
                logger.error("Invalid key action: missing keys")
                return False
        
        elif action_type == "scroll":
            # 滚动动作至少需要方向或者坐标
            if "direction" not in action and ("x" not in action or "y" not in action):
                logger.error("Invalid scroll action: missing direction or coordinates")
                return False
        
        elif action_type == "stop":
            # 停止动作是合法的
            pass
        
        else:
            logger.error("Unknown action type: {}", action_type)
            return False
        
        return True
    
    def execute(self, action):
        """执行指定的动作
        
        Args:
            action (dict,list): 动作描述，包含类型和参数
            
        Returns:
            bool: 执行是否成功
        """
        # 处理动作列表
        if isinstance(action, list):
            success = []
            for act in action:
                suc = self.execute(act)
                success.append(suc)
            return all(success)
            
        # 首先验证动作
        if not self.validate(action):
            return False
        
        action_type = action.get("type", "")
        
        try:
            # 根据动作类型执行相应操作
            if action_type == "move":
                return self._move_mouse(action)
            elif action_type == "click":
                return self._click_mouse(action)
            elif action_type == "type":
                return self._type_text(action)
            elif action_type == "key":
                 return self._press_key(action)
            elif action_type == "scroll":
                return self._scroll(action)
            elif action_type == "stop":
                logger.info("Received stop action: {}", action.get("reason", "unspecified"))
                return True
            else:
                logger.warning("Unknown action type: {}", action_type)
                return False
        except Exception as e:
            logger.exception("Error executing action {}: {}", action_type, e)
            return False
    
    def _move_mouse(self, action):
        """移动鼠标到指定位置
        
        Args:
            action (dict): 移动动作参数
            
        Returns:
            bool: 是否成功
        """
        x = action.get("x", 0)
        y = action.get("y", 0)
        duration = action.get("duration", self.move_duration)
        
        try:
            # 移动鼠标
            pyautogui.moveTo(x, y, duration=duration)
            logger.debug("Mouse moved to ({}, {})", x, y)
            return True
        except Exception as e:
            logger.exception("Error moving mouse to ({}, {}): {}", x, y, e)
            return False
    
    def _click_mouse(self, action):
        """点击鼠标
        
        Args:
            action (dict): 点击动作参数
            
        Returns:
            bool: 是否成功
        """
        x = action.get("x", None)
        y = action.get("y", None)
        button = action.get("button", "left")
        clicks = action.get("clicks", 1)
        interval = action.get("interval", 0.25)
        duration = action.get("duration", self.move_duration)
        
        try:
            if x is not None and y is not None:
                # 移动到指定位置再点击
                pyautogui.click(x, y, clicks=clicks, interval=interval, 
                               button=button, duration=duration)
                logger.debug("Mouse clicked at ({}, {}): {} clicks, {} button", 
                           x, y, clicks, button)
            else:
                # 在当前位置点击
                pyautogui.click(clicks=clicks, interval=interval, button=button)
                curr_x, curr_y = pyautogui.position()
                logger.debug("Mouse clicked at current position ({}, {}): {} clicks, {} button", 
                           curr_x, curr_y, clicks, button)
            return True
        except Exception as e:
            logger.exception("Error clicking mouse: {}", e)
            return False
    
    def _type_text(self, action):
        """输入文本
        
        Args:
            action (dict): 输入动作参数
            
        Returns:
            bool: 是否成功
        """
        text = action.get("text", "")
        interval = action.get("interval", self.type_interval)
        
        try:
            # 输入文本
            pyautogui.typewrite(text, interval=interval)
            log_text = text if len(text) < 20 else f"{text[:17]}..."
            logger.debug("Text typed: '{}' (length: {})", log_text, len(text))
            return True
        except Exception as e:
            logger.exception("Error typing text: {}", e)
            return False
    
    def _press_key(self, action):
        """按下键盘按键
        
        Args:
            action (dict): 按键动作参数
            
        Returns:
            bool: 是否成功
        """
        keys = action.get("keys", [])
        
        # 处理单个键和键盘组合
        if isinstance(keys, str):
            keys = [keys]
        
        try:
            # 按键操作
            if len(keys) == 1:
                # 单个键
                pyautogui.press(keys[0])
                logger.debug("Key pressed: {}", keys[0])
            elif len(keys) > 1:
                # 组合键
                pyautogui.hotkey(*keys)
                logger.debug("Hotkey pressed: {}", "+".join(keys))
            else:
                logger.warning("No keys specified")
                return False
            return True
        except Exception as e:
            logger.exception("Error pressing keys {}: {}", keys, e)
            return False
    
    def _scroll(self, action):
        """滚动屏幕
        
        Args:
            action (dict): 滚动动作参数
            
        Returns:
            bool: 是否成功
        """
        clicks = action.get("clicks", 1)
        direction = action.get("direction", "down")
        
        try:
            # 滚动操作
            if direction == "down":
                pyautogui.scroll(-clicks)  # 向下滚动为负值
            elif direction == "up":
                pyautogui.scroll(clicks)   # 向上滚动为正值
            elif direction == "left":
                pyautogui.hscroll(-clicks)  # 向左滚动为负值
            elif direction == "right":
                pyautogui.hscroll(clicks)   # 向右滚动为正值
            else:
                logger.warning("Unknown scroll direction: {}", direction)
                return False
                
            logger.debug("Scrolled {} {} clicks", direction, clicks)
            return True
        except Exception as e:
            logger.exception("Error scrolling: {}", e)
            return False