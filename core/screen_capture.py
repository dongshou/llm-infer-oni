"""
屏幕捕获模块 - 负责获取屏幕状态并进行处理
"""

import io
import time
import base64
import pyautogui
from loguru import logger
from base.perception import BasePerception

class ScreenCapture(BasePerception):
    """屏幕捕获模块，实现从屏幕获取状态的功能"""
    
    def __init__(self, config):
        """初始化屏幕捕获模块
        
        Args:
            config (dict): 配置参数
        """
        super().__init__(config)
        self.last_screenshot = None
        self.last_capture_time = 0
        # 捕获间隔时间，防止过于频繁的截图
        self.min_capture_interval = config.get("min_capture_interval", 0.2)
        logger.debug("Screen capture initialized with min interval: {}s", 
                    self.min_capture_interval)
    
    def capture(self):
        """捕获当前屏幕状态
        
        Returns:
            PIL.Image: 屏幕截图对象
        """
        # 检查是否需要限制捕获频率
        current_time = time.time()
        if current_time - self.last_capture_time < self.min_capture_interval:
            logger.debug("Using cached screenshot (interval: {:.2f}s)", 
                       current_time - self.last_capture_time)
            return self.last_screenshot
        
        try:
            # 使用pyautogui截取全屏
            screenshot = pyautogui.screenshot()
            self.last_screenshot = screenshot
            self.last_capture_time = current_time
            
            # 获取屏幕尺寸
            width, height = screenshot.size
            logger.debug("Screen captured: {}x{}", width, height)
            
            return screenshot
        except Exception as e:
            logger.exception("Error capturing screen: {}", e)
            return None
    
    def process(self):
        """处理屏幕截图，转换为适合决策使用的格式
        
        Returns:
            dict: 处理后的状态数据，包含图像和元数据
        """
        screenshot = self.capture()
        if screenshot is None:
            logger.error("No screenshot available to process")
            return {
                "error": "Failed to capture screen",
                "timestamp": time.time()
            }
        
        try:
            # 将截图转换为base64编码，方便传输给大模型
            buffered = io.BytesIO()
            screenshot.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # 获取屏幕尺寸
            width, height = screenshot.size
            
            # 构建状态数据
            state = {
                "image": img_str,
                "screen_width": width,
                "screen_height": height,
                "timestamp": time.time(),
                "cursor_position": pyautogui.position()  # 当前鼠标位置
            }
            
            logger.debug("Processed screen: {}x{}, cursor at {}", 
                       width, height, state["cursor_position"])
            
            return state
        except Exception as e:
            logger.exception("Error processing screenshot: {}", e)
            return {
                "error": str(e),
                "timestamp": time.time()
            }
    
    def save_screenshot(self, path=None):
        """保存当前截图到文件
        
        Args:
            path (str, optional): 保存路径，默认为基于时间戳的文件名
            
        Returns:
            str: 保存的文件路径，失败则返回None
        """
        if not path:
            path = f"screenshot_{int(time.time())}.png"
        
        if self.last_screenshot:
            try:
                self.last_screenshot.save(path)
                logger.debug("Screenshot saved to {}", path)
                return path
            except Exception as e:
                logger.exception("Error saving screenshot: {}", e)
        else:
            logger.warning("No screenshot available to save")
        
        return None