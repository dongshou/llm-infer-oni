"""
大模型决策模块 - 负责与大模型交互获取决策
"""

import json
import re
import time
from typing import Union,List
from loguru import logger
from openai import OpenAI

from base.brain import BaseBrain
from utils.prompt_manager import PromptManager


class LLMDecision(BaseBrain):
    """大模型决策模块，实现与LLM交互获取决策的功能"""
    
    def __init__(self, config):
        """初始化大模型决策模块
        
        Args:
            config (dict): 配置参数
        """
        super().__init__(config)
        # API配置
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", None)
        self.model = config.get("model", "gpt-4-vision-preview")
        self.max_tokens = config.get("max_tokens", None)
        self.temperature = config.get("temperature", 0.7)
        
        # 初始化OpenAI客户端
        client_args = {
            "api_key": self.api_key
        }
        
        # 如果有提供base_url，添加到客户端参数
        if self.base_url:
            client_args["base_url"] = self.base_url
            logger.info("使用自定义API端点: {}", self.base_url)
            
        self.client = OpenAI(**client_args)
        
        # 历史配置
        self.max_history = config.get("max_history", 5)
        
        # 初始化提示词管理器
        self.prompt_manager = PromptManager(config)
        
        logger.info("大模型决策模块初始化完成，使用模型: {}", self.model)
        logger.info("已加载{}个提示词", len(self.prompt_manager.list_prompts()))
        
        # 验证API配置
        if not self.api_key:
            logger.warning("API密钥未提供，API调用将会失败")
        
        # 请求计数器 - 用于监控API使用情况
        self.request_count = 0
    
    def decide(self, state, context):
        """根据状态和上下文决定下一步动作
        
        Args:
            state (dict): 当前环境状态，包含图像和元数据
            context (dict): 当前上下文，包含历史和任务信息
            
        Returns:
            dict: 下一步动作的描述
        """
        try:
            # 检查状态是否有效
            if not state or "error" in state:
                logger.error("无效的状态: {}", state.get("error", "未知错误"))
                return {"type": "stop", "reason": f"状态获取失败: {state.get('error', '未知错误')}"}
            
            # 获取当前使用的提示词名称
            prompt_name = context.get("prompt_name")
            
            # 获取提示词内容
            prompt_content = self.prompt_manager.get_prompt(prompt_name)
            
            # 格式化提示词
            prompt = self.prompt_manager.format_prompt(prompt_content, context)
            
            # 调用API获取回复
            full_response = self._call_api(prompt, state.get("image", ""))
            
            # 保存完整回复到上下文，供日志使用
            context["_full_model_response"] = full_response
            
            # 解析回复获取动作
            action = self._parse_response(full_response)
            
            # 记录请求计数
            self.request_count += 1
            
            return action
        except Exception as e:
            logger.exception("决策过程出错: {}", e)
            return {"type": "stop", "reason": f"决策过程错误: {str(e)}"}
    
    def set_prompt(self, name, context):
        """设置当前使用的提示词
        
        Args:
            name (str): 提示词名称
            context (dict): 当前上下文
            
        Returns:
            bool: 是否设置成功
        """
        # 使用提示词管理器设置当前提示词
        success = self.prompt_manager.set_current_prompt(name)
        
        # 如果成功，更新上下文中的提示词名称
        if success:
            context["prompt_name"] = name
        
        return success
    
    def add_prompt(self, name, content, save_to_file=True):
        """添加新的提示词
        
        Args:
            name (str): 提示词名称
            content (str): 提示词内容
            save_to_file (bool, optional): 是否保存到文件
            
        Returns:
            bool: 是否添加成功
        """
        # 添加到提示词管理器
        if name not in self.prompt_manager.prompts:
            self.prompt_manager.prompts[name] = content
            logger.info("已添加新提示词: {}", name)
            
            # 如果需要，保存到文件
            if save_to_file:
                return self.prompt_manager.save_prompt(name, content)
            
            return True
        else:
            logger.warning("提示词已存在: {}", name)
            return False
        
    def list_prompts(self):
        """列出所有可用的提示词
        
        Returns:
            list: 提示词名称列表
        """
        return self.prompt_manager.list_prompts()
    
    def get_prompt_info(self):
        """获取提示词状态信息
        
        Returns:
            dict: 提示词状态信息
        """
        return self.prompt_manager.get_prompt_info()
    
    def get_prompt_info(self):
        """获取提示词状态信息
        
        Returns:
            dict: 提示词状态信息
        """
        return self.prompt_manager.get_prompt_info()
    
    def _build_prompt(self, context):
        """构建提示信息
        
        Args:
            context (dict): 当前上下文
            
        Returns:
            str: 构建的提示信息
        """
        task = context.get("task", "")
        history = context.get("history", [])
        
        # 基础提示内容
        prompt = f"""
        你是一个能够控制电脑界面的AI助手。你能看到屏幕内容并通过鼠标和键盘操作来完成任务。
        
        当前任务: {task}
        
        你可以执行以下动作:
        1. 移动鼠标: {{"type": "move", "x": X坐标, "y": Y坐标}}
        2. 点击鼠标: {{"type": "click", "x": X坐标, "y": Y坐标, "button": "left|right|middle", "clicks": 点击次数}}
        3. 输入文本: {{"type": "type", "text": "要输入的文本"}}
        4. 按键: {{"type": "key", "keys": ["key1", "key2", ...]}}
        5. 滚动: {{"type": "scroll", "direction": "up|down|left|right", "clicks": 滚动量}}
        6. 停止: {{"type": "stop", "reason": "任务完成原因"}}
        
        坐标系统的原点(0,0)在屏幕左上角，x轴向右增加，y轴向下增加。
        
        请分析当前屏幕内容，并返回一个能够推进任务的单一动作。你的回答应该只包含一个有效的JSON格式动作，不需要其他解释。
        """
        
        # 添加历史动作
        if history:
            recent_history = history[-min(self.max_history, len(history)):]
            prompt += "\n\n最近执行的动作:\n"
            for i, item in enumerate(recent_history):
                if "action" in item and "result" in item:
                    action_str = json.dumps(item["action"], ensure_ascii=False)
                    result_str = "成功" if item["result"].get("success", False) else "失败"
                    prompt += f"{i+1}. {action_str} - {result_str}\n"
        
        return prompt
    
    def _call_api(self, prompt, image_data):
        """调用OpenAI API
        
        Args:
            prompt (str): 提示信息
            image_data (str): base64编码的图像数据
            
        Returns:
            str: API响应内容
        """
        if not self.api_key:
            logger.error("API密钥未提供")
            return "API密钥未提供"
        
        try:
            # 准备消息内容
            message_content = [
                {
                    "type": "text", 
                    "text": prompt
                }
            ]
            
            # 如果有图像数据，添加图像内容
            if image_data:
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_data}"
                    }
                })
            
            start_time = time.time()
            logger.debug("正在发送请求到OpenAI API")
            
            # 使用OpenAI客户端发送请求
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": message_content}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )
            
            elapsed = time.time() - start_time
            logger.debug("API响应已接收，耗时{:.2f}秒", elapsed)
            
            # 提取回复内容
            if response.choices and len(response.choices) > 0:
                print(response.choices[0].message.content)
                return response.choices[0].message.content
            else:
                logger.error("API响应中没有有效内容")
                return "API响应中没有有效内容"
            
        except Exception as e:
            logger.exception("调用OpenAI API时出错: {}", e)
            return f"API调用错误: {str(e)}"
    
    def _parse_response(self, response):
        """解析API响应提取动作
        
        Args:
            response (str): API响应内容
            
        Returns:
            dict,list: 解析出的动作
        """
        try:
            # 检查是否有错误信息
            if response.startswith("API"):
                logger.error("API响应错误: {}", response)
                return {"type": "stop", "reason": response}
            # 尝试提取被 ```json 包裹的JSON部分
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response, re.IGNORECASE)
            if json_match:
                json_str = json_match.group(1)  # 提取第一个捕获组（JSON内容）
                
                # 尝试解析JSON
                try:
                    action = json.loads(json_str)
                    logger.debug("已解析动作: {}", action)
                    
                    match action:
                        case dict() if "type" not in action:
                            logger.warning("无效的动作格式: 字典缺少type字段", action)
                            return {"type": "stop", "reason": "动作格式无效"}
                        case list() if not action or not isinstance(action[0], dict) or "type" not in action[0]:
                            logger.warning("无效的动作格式: 列表问题", action)
                            return {"type": "stop", "reason": "动作格式无效"}
                        case _ if not isinstance(action, (dict, list)):
                            logger.warning("无效的动作格式: 不是字典或列表", action)
                            return {"type": "stop", "reason": "动作格式无效"}

                    return action
                except json.JSONDecodeError as e:
                    logger.error("无法将响应解析为JSON: {}", e)
                    logger.debug("响应内容: {}", response)
                    return {"type": "stop", "reason": "无法解析回复为有效JSON"}
            else:
                logger.error("响应中未找到JSON格式内容")
                logger.debug("响应内容: {}", response)
                return {"type": "stop", "reason": "响应中未找到有效的动作JSON"}
        except Exception as e:
            logger.exception("解析响应时出错: {}", e)
            return {"type": "stop", "reason": f"解析错误: {str(e)}"}
            
