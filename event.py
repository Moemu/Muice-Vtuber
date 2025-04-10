from blivedm.blivedm.models.open_live import DanmakuMessage,GiftMessage,SuperChatMessage,GuardBuyMessage,RoomEnterMessage
from _types import *
from typing import Type, Tuple, List
from ui import WebUI
from utils.memory import generate_history
from utils.utils import get_avatar_base64, message_precheck, screenshot
from llm.utils.auto_system_prompt import auto_system_prompt
import random,asyncio,time

import logging

logger = logging.getLogger('Muice.Event')

# 任务队列
class EventQueue:
    def __init__(self, first_run=True) -> None:
        self.queue = asyncio.PriorityQueue(maxsize=7)
        if first_run:
            self.leisure_task: LeisureTask | None = None
        self.is_running = False
        self.first_run = first_run

    async def __run(self):
        idle_time = 0  # 记录空闲时间

        while self.is_running:
            if self.queue.empty():
                await asyncio.sleep(0.5)
                idle_time += 0.5

                if idle_time >= 50 and random.random() < 0.05:
                    # 5% 概率决定任务类型
                    if random.random() < 0.05:
                        logger.info('发布一个读屏任务...')
                        await self.__create_a_read_screen_task()
                    else:
                        logger.info('发布一个闲时任务...')
                        await self.__create_a_leisure_task()

                    idle_time = 0  # 重置空闲时间
                continue

            idle_time = 0  # 有任务时重置空闲时间

            try:
                priority, _, task_class = await self.queue.get()
            except Exception as e:
                logger.error(f"获取任务时出错: {e}")
                continue

            if not task_class:
                continue

            try:
                await task_class.run()
            except Exception as e:
                logger.error(f"执行任务时出错: {e}", exc_info=True)

            logger.debug(f"当前队列长度: {self.queue.qsize()}")

    async def __create_a_leisure_task(self):
        """
        发布一个闲时任务
        """
        await self.put(10, self.leisure_task)

    async def __create_a_read_screen_task(self):
        """
        发布了一个读屏任务
        """
        if not self.leisure_task: return
        data = MessageData()
        await self.put(10, ReadScreenTask(self.leisure_task.resource_hub, data))

    async def put(self, priority: int, event):
        timestamp = time.time()
        new_item = (priority, timestamp, event)

        if not self.queue.full():
            await self.queue.put(new_item)
            return

        # 队列满了，取出所有任务暂存
        temp_items = []
        lower_priority_items = []
        same_priority_items = []

        for _ in range(self.queue.qsize()):
            item = await self.queue.get()
            temp_items.append(item)
            item_priority, item_timestamp, _ = item

            if item_priority > priority:  # 更低优先级
                lower_priority_items.append(item)
            elif item_priority == priority:
                same_priority_items.append(item)

        replaced = False

        if lower_priority_items:
            # 替换最早插入的低优先级任务
            to_replace = min(lower_priority_items, key=lambda x: x[1])
            temp_items.remove(to_replace)
            logger.warning(f"优先级较低的事件 {to_replace} 被替换")
            replaced = True
        elif same_priority_items:
            # 替换最早插入的同优先级任务
            to_replace = min(same_priority_items, key=lambda x: x[1])
            temp_items.remove(to_replace)
            logger.warning(f"同优先级的早期事件 {to_replace} 被替换")
            replaced = True

        # 重新放回其他任务
        for item in temp_items:
            await self.queue.put(item)

        if replaced:
            await self.queue.put(new_item)
        else:
            logger.warning(f"事件 {event} 被忽略，队列中任务优先级更高")

    def start(self) -> bool:
        if self.is_running:
            logger.info('事件队列已在运行中')
            return False
        if not self.first_run:
            self.__init__(False)
        self.is_running = True
        
        asyncio.create_task(self.__run())  

        logger.info('事件队列已启动')
        return self.is_running

        
    def stop(self):
        self.is_running = False
        self.first_run = False
        logger.info('事件队列已停止')


class DanmuTask(BasicTask):
    '''弹幕任务'''
    @BasicTask.message_filter
    async def run(self):
        logger.info(f'[{self.data.username}]：{self.data.message}')
        history = await generate_history(self.resource_hub.database, self.data.message, self.data.userid)
        logger.debug(f'[{self.data.username}] 获取到的历史记录: {history}')
        
        prompt = f'<{self.data.username}> {self.data.message}'
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model_config.system_prompt
        respond = await self.model.ask(prompt=prompt, history=history, stream=False, tools=self.tools, system=system) or '(已过滤)'
        logger.info(f'[{self.data.username}] {self.data.message} -> {respond}')

        await self.post_response(respond)
        logger.info(f'[{self.data.username}] 事件处理结束')

class GiftTask(BasicTask):
    '''礼物任务'''
    async def run(self):
        logger.info(f'[{self.data.username}] 赠送了 {self.data.gift_name} x {self.data.gift_num} 总价值: {self.data.total_value}')
        respond = f"感谢 {self.data.username} 赠送的 {self.data.gift_name} 喵，雪雪最喜欢你了喵！"
        logger.info(f'[{self.data.username}] {self.data.gift_name} -> {respond}')

        await self.post_response(respond, save=False)
        await self.database.add_gift(self.data.username, self.data.userid, self.data.gift_name, self.data.total_value)
        logger.info(f'[{self.data.username}] 事件处理结束')

class SuperChatTask(BasicTask):
    '''醒目留言任务'''
    async def run(self):
        logger.info(f'[{self.data.username}] 赠送了 ¥{self.data.total_value} 醒目留言：{self.data.message}')
        history = await generate_history(self.resource_hub.database, self.data.message, self.data.userid)

        prompt = f'<{self.data.username}> {self.data.message}'
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model_config.system_prompt
        model_output = await self.model.ask(prompt=prompt, history=history, stream=False, tools=self.tools, system=system) or '(已过滤)'
        respond = f"感谢 {self.data.username} 的SuperChat。\n" + model_output
        logger.info(f'[{self.data.username}] 醒目留言 -> {respond}')

        await self.post_response(respond)
        await self.database.add_gift(self.data.username, self.data.userid, "醒目留言", self.data.total_value)
        logger.info(f'[{self.data.username}] 事件处理结束')

class BuyGuardTask(BasicTask):
    '''上舰任务'''
    async def run(self):
        logger.info(f'{self.data.username} 购买了大航海等级 {self.data.guard_level}')
        respond = f'感谢 {self.data.username} 的舰长喵！会有什么神奇的事情发生呢？'

        await self.post_response(respond, save=False)
        await self.database.add_gift(self.data.username, self.data.userid, f'大航海等级{self.data.guard_level}', self.data.total_value)

        logger.info(f'[{self.data.username}] 事件处理结束')

class LeisureTask(BasicTask):
    async def run(self):
        # history = self.database.get_history()
        active_prompts = ['<生成推文: 胡思乱想>', '<生成推文: AI生活>', '<生成推文: AI思考>', '<生成推文: 表达爱意>', '<生成推文: 情感建议>']
        prompt = random.choice(active_prompts)

        system = auto_system_prompt(self.data.message) if self.leisure_model.config.auto_system_prompt else self.leisure_model.config.system_prompt
        respond = await self.leisure_model.ask(prompt, history=[], system=system)

        await self.post_response(respond, save=False)
        await self.database.add_item('闲时任务', '0', prompt, respond)

class EnterRoomTask(BasicTask):
    async def run(self):
        logger.info(f'{self.data.username} 进入房间')
        respond = f"欢迎 {self.data.username} 进入到直播间喵"

        await self.post_response(respond, save=False)
        logger.info(f'[{self.data.username}] 事件处理结束')

class RefreshTask(BasicTask):
    async def run(self):
        logger.info(f'{self.data.username} 请求刷新')
        history = await generate_history(self.resource_hub.database, self.data.message, self.data.userid, user_only=True)
        logger.debug(f'获取到的历史记录: {history}')

        prompt = history[-1].danmu
        history = history[:-1]
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model.config.system_prompt
        respond = await self.model.ask(prompt, history=history, tools=self.tools, system=system) or '(已过滤)'
        logger.info(f'[{self.data.username}] {prompt} -> {respond}')

        await self.database.remove_last_item(self.data.userid)
        await self.post_response(respond, save=False)
        await self.database.add_item(self.data.username, self.data.userid, prompt, respond)
        logger.info(f'[{self.data.username}] 事件处理结束')

class CleanMemoryTask(BasicTask):
    async def run(self):
        logger.info(f'{self.data.username} 请求清空对话历史')
        await self.database.unavailable_item(self.data.userid)
        logger.info(f'{self.data.username} 对话历史已清空')
        respond = '对话历史已清空'

        logger.info(f'{self.data.username} TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()

        logger.info(f'[{self.data.username}] 事件处理结束')

class ReadScreenTask(BasicTask):
    async def run(self):
        logger.info('[读屏任务] 开始读取屏幕')
        respond = '让我们看一下沐沐在干什么...'
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()

        screenshot()
        image_info = await self.multimodal.ask(prompt="用简单的一段话描述一下这张图片", history=[], images=['./temp/screenshot.png'], stream=False)
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model_config.system_prompt
        respond = await self.model.ask(f'<读屏任务-沐沐的屏幕内容: {image_info}>', history=[], system=system) or '(已过滤)'
        logger.info(f'[读屏任务] <读屏任务-沐沐的屏幕内容: {image_info}> -> {respond}')

        await self.post_response(respond, save=False)
        await self.database.add_item('Muice', '0', f'<读屏任务-沐沐的屏幕内容: {image_info}>', respond)

        logger.info(f'[读屏任务] 事件处理结束')

# WebUI事件处理(总事件处理)
class WebUIEventHandler:
    def __init__(self, resource_hub: ResourceHub, webui:WebUI, danmu, queue, realtimechat) -> None:
        self.config = resource_hub.config
        self.model = resource_hub.model
        self.webui = webui
        self.danmu = danmu
        self.captions = resource_hub.captions
        self.queue = queue
        # self.bot = resource_hub.bot
        self.realtimechat = realtimechat
        self.model = resource_hub.model
        self.chat_history = []

    async def start_all(self):
        self.connect_to_LLM()
        self.connect_to_captions()
        await self.connect_to_blivedm()
        self.start_service()
    
    def start_service(self):
        if self.webui.status.all:
            self.webui.ui.notify('无法启动：已启动了一个进程',type='negative')
            return False
        if self.webui.status.llm and self.webui.status.blivedm and self.webui.status.captions:
            if self.queue.start():
                self.webui.change_all_status(1)
        else:
            self.webui.ui.notify('无法启动：必要的组件未全部连接',type='negative')

    def stop_service(self):
        if not self.webui.status.all:
            self.webui.ui.notify('无法关闭：进程未在运行中',type='negative')
            return False
        self.queue.stop()
        self.webui.change_all_status(0)

    def connect_to_LLM(self):
        if self.webui.status.llm:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        if self.model.is_running:
            self.webui.change_LLM_status(1)
        else:
            self.webui.ui.notify('无法连接至LLM',type='negative')
            return False

    async def connect_to_blivedm(self):
        if self.webui.status.blivedm:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        self.danmu.start_client()

    async def disconnect_to_blivedm(self):
        if not self.webui.status.blivedm:
            self.webui.ui.notify('尚未连接！',type='negative')
            return False
        self.danmu.close_client()

    def connect_to_captions(self):
        if self.webui.status.captions:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        if self.captions.connect():
            self.webui.change_captions_status(1)
        else:
            self.webui.ui.notify('无法连接至字幕组件',type='negative')

    def start_realtime_chat(self):
        if self.webui.status.realtime_chat:
            self.webui.ui.notify('不能重复启动！',type='negative')
            return False
        if not self.model.is_running:
            self.webui.ui.notify('LLM未连接',type='negative')
            return
        self.webui.change_realtime_chat_status(1)
        self.realtimechat.register_keyboard()
        if self.queue.is_running:
            self.queue.stop()

    def stop_realtime_chat(self):
        if not self.webui.status.realtime_chat:
            self.webui.ui.notify('未启动！',type='negative')
            return False
        self.webui.change_realtime_chat_status(0)
        self.realtimechat.unregister_keyboard()
        if not self.queue.is_running:
            self.queue.start()

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

# 弹幕事件处理分发
class DanmuEventHandler:
    def __init__(self, resource_hub:ResourceHub, quene, ui:WebUI) -> None:
        self.resource_hub = resource_hub
        self.model = resource_hub.model
        self.tts = resource_hub.tts
        self.captions = resource_hub.captions
        self.database = resource_hub.database
        self.quene = quene
        self.ui = ui

    def shutdown(self):
        '''Blivedm退出'''
        self.quene.stop()
        self.ui.change_all_status(0)
        self.ui.change_blivedm_status(0)
        logger.info('事件处理已暂停')

    async def DanmuEvent(self, danmu:DanmakuMessage):
        if self.ui.ui_danmu:
            self.ui.ui_danmu.push(f'{danmu.uname}：{danmu.msg}')
        message = danmu.msg
        username = danmu.uname
        userface = danmu.uface
        userid = danmu.open_id
        fans_medal_level = danmu.fans_medal_level
        if not all((self.model.is_running, self.captions.is_connecting, message_precheck(message))):
            return
        userface = await get_avatar_base64(userface + '@250x250')

        data = MessageData(username, userid, userface, message)
        task_cls, priority = CommandTask.get_task(message)
        task = task_cls(self.resource_hub, data)
        priority = 4 if fans_medal_level else priority
        await self.quene.put(priority, task)


    async def GiftEvent(self, gift:GiftMessage):
        if not gift.paid: return  # 不给钱的不读
        username = gift.uname
        userid = gift.open_id
        gift_name = gift.gift_name
        gift_num = gift.gift_num
        total_value = gift.price * gift.gift_num / 1000
        data = MessageData(username, userid, gift_name=gift_name, gift_num=gift_num, total_value=total_value)
        task = GiftTask(self.resource_hub, data)
        await self.quene.put(3, task)

    async def SuperChatEvent(self, superchat:SuperChatMessage):
        username = superchat.uname
        userid = superchat.open_id
        message = superchat.message
        userface = superchat.uface
        rmb = float(superchat.rmb)
        userface = await get_avatar_base64(userface + '@250x250')
        data = MessageData(username, userid, userface, message, total_value=rmb)
        task = SuperChatTask(self.resource_hub, data)
        await self.quene.put(1, task)

    async def GuardBuyEvent(self, message:GuardBuyMessage):
        username = message.user_info.uname
        userid = message.user_info.open_id
        guard_level = message.guard_level
        price = message.price / 1000
        data = MessageData(username=username, userid=userid, guard_level=guard_level, total_value=price)
        task = BuyGuardTask(self.resource_hub, data)
        await self.quene.put(1, task)

    async def EnterRoomEvent(self, message:RoomEnterMessage):
        username = message.uname
        data = MessageData(username=username)
        task = EnterRoomTask(self.resource_hub, data)
        await self.quene.put(10, task)