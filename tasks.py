from models import BasicTask
from utils.memory import generate_history
from utils.utils import screenshot
from llm.utils.auto_system_prompt import auto_system_prompt
from typing import List, Type, Tuple
import logging
import random

logger = logging.getLogger("Muice.task")

class DanmuTask(BasicTask):
    '''弹幕任务'''
    # @BasicTask.message_filter
    async def pretreatment(self) -> bool:
        logger.info(f'[{self.data.username}]：{self.data.message}')
        history = await generate_history(self.database, self.data.message, self.data.userid)
        
        prompt = f'<{self.data.username}> {self.data.message}'
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model_config.system_prompt
        self.response = await self.model.ask(prompt=prompt, history=history, stream=False, tools=self.tools, system=system) or '(已过滤)'
        logger.info(f'[{self.data.username}] {self.data.message} -> {self.response}')

        logger.info(f'[{self.data.username}] TTS处理...')
        self.tts_file = await self.tts.generate_tts(self.response)
        if not self.tts_file:
            return False
        
        logger.info(f'[{self.data.username}] 事件预处理结束')
        return True

class GiftTask(BasicTask):
    '''礼物任务'''
    async def pretreatment(self) -> bool:
        logger.info(f'[{self.data.username}] 赠送了 {self.data.gift_name} x {self.data.gift_num} 总价值: {self.data.total_value}')
        self.response = f"感谢 {self.data.username} 赠送的 {self.data.gift_name} 喵，雪雪最喜欢你了喵！"
        logger.info(f'[{self.data.username}] {self.data.gift_name} -> {self.response}')

        logger.info(f'[{self.data.username}] TTS处理...')
        self.tts_file = await self.tts.generate_tts(self.response)
        if not self.tts_file:
            return False

        await self.database.add_gift(self.data.username, self.data.userid, self.data.gift_name, self.data.total_value)
        self.is_saved = True

        logger.info(f'[{self.data.username}] 事件预处理结束')
        return True

class SuperChatTask(BasicTask):
    '''醒目留言任务'''
    async def pretreatment(self) -> bool:
        logger.info(f'[{self.data.username}] 赠送了 ¥{self.data.total_value} 醒目留言：{self.data.message}')
        history = await generate_history(self.database, self.data.message, self.data.userid)

        prompt = f'<{self.data.username}> {self.data.message}'
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model_config.system_prompt
        model_output = await self.model.ask(prompt=prompt, history=history, stream=False, tools=self.tools, system=system) or '(已过滤)'
        self.response = f"感谢 {self.data.username} 的SuperChat。\n" + model_output
        logger.info(f'[{self.data.username}] 醒目留言 -> {self.response}')

        logger.info(f'[{self.data.username}] TTS处理...')
        self.tts_file = await self.tts.generate_tts(self.response)
        if not self.tts_file:
            return False

        await self.database.add_gift(self.data.username, self.data.userid, "醒目留言", self.data.total_value)

        logger.info(f'[{self.data.username}] 事件预处理结束')
        return True

class BuyGuardTask(BasicTask):
    '''上舰任务'''
    async def pretreatment(self) -> bool:
        logger.info(f'{self.data.username} 购买了大航海等级 {self.data.guard_level}')
        self.response = f'感谢 {self.data.username} 的舰长喵！会有什么神奇的事情发生呢？'

        logger.info(f'[{self.data.username}] TTS处理...')
        self.tts_file = await self.tts.generate_tts(self.response)
        if not self.tts_file:
            return False

        await self.database.add_gift(self.data.username, self.data.userid, f'大航海等级{self.data.guard_level}', self.data.total_value)
        self.is_saved = True

        logger.info(f'[{self.data.username}] 事件预处理结束')
        return True

class LeisureTask(BasicTask):
    async def pretreatment(self) -> bool:
        # history = self.database.get_history()
        active_prompts = ['<生成推文: 胡思乱想>', '<生成推文: AI生活>', '<生成推文: AI思考>', '<生成推文: 表达爱意>', '<生成推文: 情感建议>']
        prompt = random.choice(active_prompts)

        system = auto_system_prompt(prompt) if self.leisure_model.config.auto_system_prompt else self.leisure_model.config.system_prompt
        self.response = await self.leisure_model.ask(prompt, history=[], system=system)

        self.tts_file = await self.tts.generate_tts(self.response)
        if not self.tts_file:
            return False
        
        await self.database.add_item('闲时任务', '0', prompt, self.response)
        self.is_saved = True

        return True

class EnterRoomTask(BasicTask):
    async def pretreatment(self) -> bool:
        logger.info(f'{self.data.username} 进入房间')
        self.response = f"欢迎 {self.data.username} 进入到直播间喵"

        self.tts_file = await self.tts.generate_tts(self.response)
        if not self.tts_file:
            return False

        self.is_saved = True
        logger.info(f'[{self.data.username}] 事件预处理结束')

        return True

class RefreshTask(BasicTask):
    async def pretreatment(self) -> bool:
        logger.info(f'{self.data.username} 请求刷新')
        history = await generate_history(self.database, self.data.message, self.data.userid, user_only=True)
        logger.debug(f'获取到的历史记录: {history}')

        prompt = history[-1].danmu
        history = history[:-1]
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model.config.system_prompt
        self.response = await self.model.ask(prompt, history=history, tools=self.tools, system=system) or '(已过滤)'
        logger.info(f'[{self.data.username}] {prompt} -> {self.response}')

        self.tts_file = await self.tts.generate_tts(self.response)
        if not self.tts_file:
            return False

        await self.database.remove_last_item(self.data.userid)
        await self.database.add_item(self.data.username, self.data.userid, prompt, self.response)
        self.is_saved = True

        logger.info(f'[{self.data.username}] 事件预处理结束')

        return True

class CleanMemoryTask(BasicTask):
    async def pretreatment(self) -> bool:
        logger.info(f'{self.data.username} 请求清空对话历史')
        await self.database.unavailable_item(self.data.userid)
        logger.info(f'{self.data.username} 对话历史已清空')
        self.response = '对话历史已清空'

        logger.info(f'{self.data.username} TTS处理...')
        if not await self.tts.generate_tts(self.response): return False

        self.is_saved = True
        logger.info(f'[{self.data.username}] 事件预处理结束')

        return True

class ReadScreenTask(BasicTask):
    async def pretreatment(self) -> bool:
        logger.info('[读屏任务] 开始读取屏幕')
        respond = '让我们看一下沐沐在干什么...'
        if not await self.tts.generate_tts(respond): return False
        await self.captions.post(respond=respond)
        await self.tts.play_audio()

        screen_image = screenshot()
        image_info = await self.multimodal.ask(prompt="用简单的一段话描述一下这张图片", history=[], images=[screen_image], stream=False)
        system = auto_system_prompt(image_info) if self.model_config.auto_system_prompt else self.model_config.system_prompt
        self.respond = await self.model.ask(f'<读屏任务-沐沐的屏幕内容: {image_info}>', history=[], system=system) or '(已过滤)'
        logger.info(f'[读屏任务] <读屏任务-沐沐的屏幕内容: {image_info}> -> {respond}')

        await self.database.add_item('Muice', '0', f'<读屏任务-沐沐的屏幕内容: {image_info}>', respond)

        logger.info(f'[读屏任务] 事件处理结束')
        return True

class DevMicrophoneTask(BasicTask):
    async def pretreatment(self) -> bool:
        logger.info(f'[Dev] {self.data.message}')

        prompt = f'<{self.data.username}> {self.data.message}'
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model_config.system_prompt
        history = await generate_history(self.database, self.data.message, '沐沐')
        self.response = await self.model.ask(prompt=prompt, history=history, stream=False, tools=self.tools, system=system) or '(已过滤)'
        logger.info(f'[Dev] {self.data.message} -> {self.response}')

        await self.database.add_item("沐沐", "0", self.data.message, self.response)
        self.is_saved = True
        logger.info(f'[{self.data.username}] 事件处理结束')
        return True
    
class CommandTask:
    """
    CommandTask类用于基于关键词注册和获取任务处理器。该类作为系统中命令任务的注册表，
    允许动态映射命令关键词和对应的任务处理类。
    """
    _rules: List[Tuple[str, Type[BasicTask], int]] = []

    @classmethod
    def register(cls, keyword: str, task_cls: Type[BasicTask], priority: int = 10) -> None:
        """
        注册新的命令任务规则
        
        :keyword: 指令关键字
        :task_cls: 指令任务类
        :priority: 指令优先级
        """
        cls._rules.append((keyword, task_cls, priority))

    @classmethod
    def get_task(cls, message:str) -> Tuple[Type[BasicTask], int]:
        """
        根据注册的规则为给定消息确定适当的任务类，若无匹配规则则返回默认任务
        """
        for keyword, task_cls, priority in cls._rules:
            if message.startswith(keyword):
                return task_cls, priority
    
        return DanmuTask, 5 

# 注册任务
CommandTask.register('刷新', RefreshTask, 10)
CommandTask.register('清空对话历史', CleanMemoryTask, 10)