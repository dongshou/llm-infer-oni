"""
提示词管理模块 - 负责管理和处理系统中使用的提示词
"""

import os
import json
import time
import shutil
from pathlib import Path
from loguru import logger

class PromptManager:
    """提示词管理器，负责提示词的加载、存储和管理"""
    
    def __init__(self, config=None):
        """初始化提示词管理器
        
        Args:
            config (dict, optional): 配置参数
        """
        self.config = config or {}
        
        # 提示词存储目录
        self.prompt_dir = self.config.get("prompt_dir", "prompts")
        
        # 备份目录
        self.backup_dir = os.path.join(self.prompt_dir, "backups")
        
        # 当前使用的提示词名称
        self.current_prompt = self.config.get("default_prompt_name", "default")
        
        # 提示词集合
        self.prompts = {}
        
        # 确保目录存在
        self._ensure_dirs()
        
        # 创建默认提示词（如果不存在）
        self._ensure_default_prompt()
        
        # 加载提示词
        self.load_prompts()
        
        logger.info("提示词管理器初始化完成，加载了{}个提示词", len(self.prompts))
    
    def _ensure_dirs(self):
        """确保所需目录存在"""
        # 创建提示词目录
        if not os.path.exists(self.prompt_dir):
            os.makedirs(self.prompt_dir)
            logger.info("创建提示词目录: {}", self.prompt_dir)
        
        # 创建备份目录
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.debug("创建提示词备份目录: {}", self.backup_dir)
    
    def _ensure_default_prompt(self):
        """确保默认提示词存在"""
        default_prompt_path = os.path.join(self.prompt_dir, "default.txt")
        
        if not os.path.exists(default_prompt_path):
            default_prompt = """
            你是一个能够控制电脑界面的AI助手。你能看到屏幕内容并通过鼠标和键盘操作来完成任务。
            
            当前任务: {task}
            
            你可以执行以下动作:
            1. 移动鼠标: {"type": "move", "x": X坐标, "y": Y坐标}
            2. 点击鼠标: {"type": "click", "x": X坐标, "y": Y坐标, "button": "left|right|middle", "clicks": 点击次数}
            3. 输入文本: {"type": "type", "text": "要输入的文本"}
            4. 按键: {"type": "key", "keys": ["key1", "key2", ...]}
            5. 滚动: {"type": "scroll", "direction": "up|down|left|right", "clicks": 滚动量}
            6. 停止: {"type": "stop", "reason": "任务完成原因"}
            
            坐标系统的原点(0,0)在屏幕左上角，x轴向右增加，y轴向下增加。
            
            最近执行的动作:
            {history}
            
            请分析当前屏幕内容，并返回一个能够推进任务的单一动作。你的回答应该只包含一个有效的JSON格式动作，不需要其他解释。
            """
            
            try:
                with open(default_prompt_path, 'w', encoding='utf-8') as f:
                    f.write(default_prompt.strip())
                logger.info("创建默认提示词文件: {}", default_prompt_path)
            except Exception as e:
                logger.error("创建默认提示词文件失败: {}", e)
    
    def _create_example_prompts(self):
        """创建示例提示词（如果配置中有指定）"""
        prompt_names = self.config.get("prompt_names", [])
        
        # 跳过默认提示词（已经创建）
        if "default" in prompt_names:
            prompt_names.remove("default")
        
        # 创建浏览器提示词
        if "browser" in prompt_names and not os.path.exists(os.path.join(self.prompt_dir, "browser.txt")):
            browser_prompt = """
            你是一个专门操作浏览器的AI助手。你的任务是：{task}
            
            当前浏览器窗口显示在屏幕上。你需要通过分析屏幕内容，找到相关元素并进行操作。
            
            你可以执行以下动作:
            1. 移动鼠标: {"type": "move", "x": X坐标, "y": Y坐标}
            2. 点击鼠标: {"type": "click", "x": X坐标, "y": Y坐标, "button": "left|right|middle", "clicks": 点击次数}
            3. 输入文本: {"type": "type", "text": "要输入的文本"}
            4. 按键: {"type": "key", "keys": ["key1", "key2", ...]}
            5. 滚动: {"type": "scroll", "direction": "up|down|left|right", "clicks": 滚动量}
            6. 停止: {"type": "stop", "reason": "任务完成原因"}
            
            浏览器常用元素位置指南：
            - 地址栏通常在窗口顶部
            - 标签页在地址栏上方
            - 导航按钮(后退、前进、刷新)在窗口左上角
            - 搜索框通常在页面中央或右上角
            
            最近执行的动作:
            {history}
            
            请分析当前屏幕内容，并返回一个有效的JSON格式动作，不需要其他解释。
            """
            self.save_prompt("browser", browser_prompt.strip(), overwrite=True)
        
        # 创建文本输入提示词
        if "text_input" in prompt_names and not os.path.exists(os.path.join(self.prompt_dir, "text_input.txt")):
            text_input_prompt = """
            你是一个专门处理文本输入的AI助手。你的任务是：{task}
            
            你需要在文本输入区域中输入内容。首先识别文本输入框的位置，然后点击它，最后输入所需文本。
            
            你可以执行以下动作:
            1. 移动鼠标: {"type": "move", "x": X坐标, "y": Y坐标}
            2. 点击鼠标: {"type": "click", "x": X坐标, "y": Y坐标, "button": "left|right|middle", "clicks": 点击次数}
            3. 输入文本: {"type": "type", "text": "要输入的文本"}
            4. 按键: {"type": "key", "keys": ["key1", "key2", ...]}
            5. 停止: {"type": "stop", "reason": "任务完成原因"}
            
            文本输入技巧：
            - 先点击输入框，确保它处于激活状态
            - 如果有现有文本，可能需要先清除（Ctrl+A 然后删除）
            - 完成输入后，通常需要按Enter键提交
            
            最近执行的动作:
            {history}
            
            请分析当前屏幕内容，并返回一个有效的JSON格式动作，不需要其他解释。
            """
            self.save_prompt("text_input", text_input_prompt.strip(), overwrite=True)
        
        # 创建办公软件提示词
        if "office" in prompt_names and not os.path.exists(os.path.join(self.prompt_dir, "office.txt")):
            office_prompt = """
            你是一个专门操作办公软件的AI助手。你的任务是：{task}
            
            你需要分析屏幕内容，识别办公软件（如Word、Excel、PowerPoint）的界面元素，并执行相应的操作。
            
            你可以执行以下动作:
            1. 移动鼠标: {"type": "move", "x": X坐标, "y": Y坐标}
            2. 点击鼠标: {"type": "click", "x": X坐标, "y": Y坐标, "button": "left|right|middle", "clicks": 点击次数}
            3. 输入文本: {"type": "type", "text": "要输入的文本"}
            4. 按键: {"type": "key", "keys": ["key1", "key2", ...]}
            5. 滚动: {"type": "scroll", "direction": "up|down|left|right", "clicks": 滚动量}
            6. 停止: {"type": "stop", "reason": "任务完成原因"}
            
            办公软件界面指南：
            - 菜单栏通常在窗口顶部
            - 工具栏在菜单栏下方
            - Word: 文档编辑区域占据大部分窗口
            - Excel: 电子表格网格占据大部分窗口
            - PowerPoint: 幻灯片编辑区域在中央
            
            最近执行的动作:
            {history}
            
            请分析当前屏幕内容，并返回一个有效的JSON格式动作，不需要其他解释。
            """
            self.save_prompt("office", office_prompt.strip(), overwrite=True)
    
    def load_prompts(self):
        """从目录加载所有提示词"""
        # 清空现有提示词
        self.prompts = {}
        
        # 从文件加载提示词
        if os.path.exists(self.prompt_dir):
            # 首先尝试加载配置中指定的提示词
            prompt_names = self.config.get("prompt_names", [])
            for name in prompt_names:
                file_path = os.path.join(self.prompt_dir, f"{name}.txt")
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            self.prompts[name] = content
                            logger.debug("已加载指定提示词: {}", name)
                    except Exception as e:
                        logger.error("加载提示词文件失败 {}: {}", file_path, e)
            
            # 然后加载目录中的所有其他提示词文件
            for file_path in Path(self.prompt_dir).glob("*.txt"):
                if file_path.is_file():
                    name = file_path.stem
                    if name not in self.prompts:  # 避免重复加载
                        try:
                            content = file_path.read_text(encoding="utf-8")
                            self.prompts[name] = content
                            logger.debug("从文件加载提示词: {}", name)
                        except Exception as e:
                            logger.error("加载提示词文件失败 {}: {}", file_path, e)
            
            # 加载JSON格式的提示词集合
            for file_path in Path(self.prompt_dir).glob("*.json"):
                if file_path.is_file():
                    try:
                        prompts_data = json.loads(file_path.read_text(encoding="utf-8"))
                        if isinstance(prompts_data, dict):
                            for name, content in prompts_data.items():
                                if name not in self.prompts:  # 避免重复加载
                                    self.prompts[name] = content
                                    logger.debug("从JSON加载提示词: {}", name)
                    except Exception as e:
                        logger.error("加载JSON提示词文件失败 {}: {}", file_path, e)
        
        # 检查是否加载了默认提示词
        if "default" not in self.prompts:
            logger.warning("未能加载默认提示词，将重新创建")
            self._ensure_default_prompt()
            self.load_prompts()  # 重新加载
            return
        
        # 创建示例提示词（如果配置中有指定）
        self._create_example_prompts()
        
        logger.info("已加载{}个提示词", len(self.prompts))
        return len(self.prompts)
    
    def save_prompt(self, name, content, overwrite=False):
        """保存提示词到文件
        
        Args:
            name (str): 提示词名称
            content (str): 提示词内容
            overwrite (bool, optional): 是否覆盖现有文件
            
        Returns:
            bool: 是否保存成功
        """
        # 确保目录存在
        self._ensure_dirs()
        
        # 如果存在且不允许覆盖，先备份
        file_path = os.path.join(self.prompt_dir, f"{name}.txt")
        if os.path.exists(file_path) and not overwrite:
            backup_path = os.path.join(
                self.backup_dir, 
                f"{name}_{int(time.time())}.txt"
            )
            try:
                shutil.copy2(file_path, backup_path)
                logger.debug("备份提示词: {} -> {}", file_path, backup_path)
            except Exception as e:
                logger.error("备份提示词失败: {}", e)
        
        # 保存提示词到文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # 同时更新内存中的提示词
            self.prompts[name] = content
            
            logger.info("提示词已保存: {}", name)
            return True
        except Exception as e:
            logger.error("保存提示词失败 {}: {}", name, e)
            return False
    
    def delete_prompt(self, name, backup=True):
        """删除提示词
        
        Args:
            name (str): 提示词名称
            backup (bool, optional): 是否备份
            
        Returns:
            bool: 是否删除成功
        """
        if name == "default":
            logger.warning("不能删除默认提示词")
            return False
        
        # 如果存在于内存中，先删除
        if name in self.prompts:
            # 备份到文件
            if backup:
                self.save_prompt(f"{name}_deleted", self.prompts[name], overwrite=True)
            
            # 从内存中删除
            del self.prompts[name]
            
            # 如果当前使用的是被删除的提示词，切换到默认提示词
            if self.current_prompt == name:
                self.current_prompt = "default"
                logger.info("当前提示词已切换到默认提示词")
        
        # 删除文件
        file_path = os.path.join(self.prompt_dir, f"{name}.txt")
        if os.path.exists(file_path):
            try:
                # 如果需要备份，移动到备份目录
                if backup:
                    backup_path = os.path.join(
                        self.backup_dir, 
                        f"{name}_{int(time.time())}.txt"
                    )
                    shutil.move(file_path, backup_path)
                    logger.debug("备份并删除提示词文件: {} -> {}", file_path, backup_path)
                else:
                    os.remove(file_path)
                    logger.debug("删除提示词文件: {}", file_path)
                
                logger.info("提示词已删除: {}", name)
                return True
            except Exception as e:
                logger.error("删除提示词文件失败 {}: {}", name, e)
                return False
        
        return True
    
    def get_prompt(self, name=None):
        """获取指定名称的提示词
        
        Args:
            name (str, optional): 提示词名称，为None则返回当前使用的提示词
            
        Returns:
            str: 提示词内容
        """
        if name is None:
            name = self.current_prompt
        
        # 如果找不到指定提示词，返回默认提示词
        if name not in self.prompts:
            logger.warning("提示词不存在: {}，使用默认提示词", name)
            return self.prompts.get("default", "")
        
        return self.prompts[name]
    
    def set_current_prompt(self, name):
        """设置当前使用的提示词
        
        Args:
            name (str): 提示词名称
            
        Returns:
            bool: 是否设置成功
        """
        if name not in self.prompts:
            logger.warning("提示词不存在: {}", name)
            return False
        
        self.current_prompt = name
        logger.info("当前提示词已设置为: {}", name)
        return True
    
    def list_prompts(self):
        """获取所有提示词的名称列表
        
        Returns:
            list: 提示词名称列表
        """
        return list(self.prompts.keys())
    
    def get_prompt_info(self):
        """获取提示词状态信息
        
        Returns:
            dict: 提示词状态信息
        """
        return {
            "current": self.current_prompt,
            "count": len(self.prompts),
            "prompts": self.list_prompts(),
            "default": "default" in self.prompts
        }
    
    def format_prompt(self, prompt_content, context):
        """格式化提示词，替换变量
        
        Args:
            prompt_content (str): 提示词内容
            context (dict): 上下文数据
            
        Returns:
            str: 格式化后的提示词
        """
        # 获取任务描述
        task = context.get("task", "")
        
        # 获取历史记录
        history_text = ""
        history = context.get("history", [])
        if history:
            max_history = self.config.get("max_history", 5)
            recent_history = history[-min(max_history, len(history)):]
            for i, item in enumerate(recent_history):
                if "action" in item and "result" in item:
                    action_str = json.dumps(item["action"], ensure_ascii=False)
                    result_str = "成功" if item["result"].get("success", False) else "失败"
                    history_text += f"{i+1}. {action_str} - {result_str}\n"
        
        # 替换基本变量
        result = prompt_content.replace("{task}", task)
        result = result.replace("{history}", history_text)
        
        # 替换自定义变量
        custom_vars = context.get("prompt_vars", {})
        for var_name, var_value in custom_vars.items():
            placeholder = "{" + var_name + "}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))
        
        return result
    
    def import_prompts(self, file_path, overwrite=False):
        """从文件导入提示词
        
        Args:
            file_path (str): 文件路径
            overwrite (bool, optional): 是否覆盖现有提示词
            
        Returns:
            int: 导入的提示词数量
        """
        try:
            path = Path(file_path)
            
            # 如果是JSON文件，尝试作为集合导入
            if path.suffix.lower() == '.json':
                prompts_data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(prompts_data, dict):
                    count = 0
                    for name, content in prompts_data.items():
                        if name != "default" or overwrite:
                            self.prompts[name] = content
                            count += 1
                            # 同时保存到文件
                            self.save_prompt(name, content, overwrite=overwrite)
                    
                    logger.info("从JSON导入了{}个提示词", count)
                    return count
            
            # 如果是单个提示词文件
            elif path.suffix.lower() == '.txt':
                name = path.stem
                content = path.read_text(encoding="utf-8")
                
                if name != "default" or overwrite:
                    self.prompts[name] = content
                    # 同时保存到文件
                    self.save_prompt(name, content, overwrite=overwrite)
                    
                    logger.info("导入了提示词: {}", name)
                    return 1
            
            logger.warning("不支持的文件格式: {}", file_path)
            return 0
            
        except Exception as e:
            logger.error("导入提示词失败: {}", e)
            return 0