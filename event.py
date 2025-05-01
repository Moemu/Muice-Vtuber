from blivedm.blivedm.models.open_live import DanmakuMessage,GiftMessage,SuperChatMessage,GuardBuyMessage,RoomEnterMessage
from _types import BasicTask, MessageData, ResourceHub
from typing import Type, Tuple, List, Optional
from ui import WebUI
from utils.memory import generate_history
from utils.utils import get_avatar_base64, message_precheck, screenshot
from llm.utils.auto_system_prompt import auto_system_prompt
import random,asyncio,time
from threading import Thread

import logging

logger = logging.getLogger('Muice.Event')

class AsyncQueueThread(Thread):
    def __init__(self, pretreat_queue: "PretreatQueue"):
        super().__init__(daemon=True)
        self.pretreat_queue = pretreat_queue

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.pretreat_queue.run_forever())


class PretreatQueue:
    """
    预处理队列
    """
    def __init__(self ,first_run=True) -> None:
        self._queue = asyncio.PriorityQueue(maxsize=7)
        self.post_queue = PostProcessQueue()

        self.DECAY_FACTOR = 0.5
        """每事件衰减因子（每轮处理后添加多少优先数）"""
        self.MAX_PRIORITY = 15
        """最大优先数限制，等于或大于此优先数的任务将被丢弃"""

        if first_run:
            self.leisure_task: Optional[LeisureTask] = None
        self.is_running = False
        self.idle_time = 0
        self.first_run = first_run

    async def _queue_get(self) -> Tuple[float, BasicTask]:
        return await self._queue.get()
    
    async def _queue_put(self, priority:float, task: BasicTask):
        await self._queue.put((priority, task))

    async def _process_queue(self) -> List[Tuple[float, BasicTask]]:
        """
        获取队列内容并过滤优先级超过阈值的任务
        """
        current_time = time.time()
        queue_items:List[Tuple[float, BasicTask]] = []
        
        while not self._queue.empty():
            priority, task = await self._queue_get()
            priority += self.DECAY_FACTOR

            # 动态优先级过滤
            if priority >= self.MAX_PRIORITY:
                logger.warning(f"任务过滤 {task} (动态优先级={priority:.1f})")
                continue

            queue_items.append((priority, task))
        
        return queue_items

    def get_priority_snapshot(self):
        """
        观察目前的队列情况
        """
        snapshot = list(self._queue._queue)  # type:ignore
        logger.debug([(item[0], item[1]) for item in snapshot])
    
    async def _get_a_leisure_task(self):
        """
        尝试发布一个空闲任务
        """
        self.idle_time += 0.5
        if self.idle_time >= 50 and random.random() < 0.05:
            # 5% 概率决定任务类型
            if random.random() < 0.05:
                logger.info('发布一个读屏任务...')
                await self.__create_a_read_screen_task()
            else:
                logger.info('发布一个闲时任务...')
                await self.__create_a_leisure_task()

            self.idle_time = 0  # 重置空闲时间

    async def __run(self):
        """任务处理主循环"""
        self.is_running = True

        while self.is_running:
            await asyncio.sleep(0.5)

            # 当主处理队列已满时，应继续等待
            if self.post_queue.is_queue_full:
                continue

            # 当队列为空时，尝试生成闲时任务
            if self._queue.empty():
                await self._get_a_leisure_task()
                continue

            # 动态优先级算法
            # 1. 取出所有任务，计算动态优先级并过滤优先数较大的任务
            if not (items := await self._process_queue()):
                continue

            # 2. 按动态优先级排序
            items.sort(key=lambda x: (x[0], x[1]))

            # 3. 处理最高优先级任务
            priority, task = items[0]

            try:
                logger.info(f"执行任务: {task} (动态优先级={priority})")
                await task.pretreatment()
                await self.post_queue.put(priority, task)
            except Exception as e:
                logger.error(f"任务执行失败: {e}", exc_info=True)

            # 4. 将剩余任务重新入队（保持原始格式）
            for item in items[1:]:
                await self._queue_put(item[0], item[1])

    async def run_forever(self):
        """主运行循环（提供给线程运行）"""
        self.is_running = True
        await self.post_queue.start_async()  # 改为 await 启动
        await self.__run()

    async def put(self, priority: int, task: BasicTask):
        """入队方法"""
        if not self._queue.full():
            await self._queue_put(priority, task)
            logger.debug(f"入队成功: {task} (优先级={priority})")
            return

        # 队列已满时的替换策略
        # 1. 取出所有任务，计算动态优先级并过滤优先数较大的任务
        queue_items = await self._process_queue()

        # 2. 添加新任务到临时列表
        queue_items.append((priority, task))

        # 3. 按动态优先级排序（优先级数值越小、时间越晚越优先）
        queue_items.sort(key=lambda x: (x[0], -x[1].time))

        # 4. 抛弃优先级数值最大、时间最早的事件
        queue_items.pop()

        logger.debug(f"队列满处理后状态:\n{self.get_priority_snapshot()}")

    def start(self):
        if self.is_running:
            logger.info('事件队列已在运行中')
            return False
        if not self.first_run:
            self.__init__(False)
        self.is_running = True

        # 启动后台线程，运行事件队列
        AsyncQueueThread(self).start()

        logger.info('事件队列已启动')
        return True

        
    def stop(self):
        self.is_running = False
        self.first_run = False
        self.post_queue.is_running = False
        logger.info('事件队列已停止')

    async def __create_a_leisure_task(self):
        """
        发布一个闲时任务
        """
        if not self.leisure_task: return
        await self.put(10, self.leisure_task)

    async def __create_a_read_screen_task(self):
        """
        发布了一个读屏任务
        """
        if not self.leisure_task: return
        data = MessageData()
        await self.put(10, ReadScreenTask(self.leisure_task.resource_hub, data))

class PostProcessQueue:
    """
    正式处理队列
    """
    def __init__(self) -> None:
        self._queue = asyncio.PriorityQueue(maxsize=1)  # 队列长度1
        self.is_running = False
        self.is_task_running = False

    async def _queue_get(self) -> Tuple[float, BasicTask]:
        return await self._queue.get()
    
    async def _queue_put(self, priority:float, task: BasicTask):
        await self._queue.put((priority, task))
    
    @property
    def is_queue_full(self) -> bool:
        return self._queue.full()

    async def __run(self):
        """主处理循环"""
        self.is_running = True
        while self.is_running:
            if self._queue.empty():
                await asyncio.sleep(0.5)
                continue

            self.is_task_running = True

            try:
                priority, task = await self._queue_get()
                logger.info(f"正式处理任务: {task}")
                await task.post_response()
            except Exception as e:
                logger.error(f"正式处理失败: {e}", exc_info=True)
            
            self.is_task_running = False

    async def put(self, priority: float, task:BasicTask):
        """入队方法"""        
        if self._queue.full():
            # 队列满时直接替换
            old_task = await self._queue_get()
            logger.warning(f"正式队列替换旧任务: {old_task[1]} → {task}")
        
        await self._queue_put(priority, task)

    async def start_async(self):
        """提供异步启动方法，供 PretreatQueue 调用"""
        if self.is_running:
            return
        self.is_running = True
        asyncio.create_task(self.__run())

    def stop(self):
        self.is_running = False


class DanmuTask(BasicTask):
    '''弹幕任务'''
    # @BasicTask.message_filter
    async def pretreatment(self) -> bool:
        logger.info(f'[{self.data.username}]：{self.data.message}')
        history = await generate_history(self.resource_hub.database, self.data.message, self.data.userid)
        logger.debug(f'[{self.data.username}] 获取到的历史记录: {history}')
        
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
        history = await generate_history(self.resource_hub.database, self.data.message, self.data.userid)

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

        system = auto_system_prompt(self.data.message) if self.leisure_model.config.auto_system_prompt else self.leisure_model.config.system_prompt
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
        history = await generate_history(self.resource_hub.database, self.data.message, self.data.userid, user_only=True)
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

        screenshot()
        image_info = await self.multimodal.ask(prompt="用简单的一段话描述一下这张图片", history=[], images=['./temp/screenshot.png'], stream=False)
        system = auto_system_prompt(self.data.message) if self.model_config.auto_system_prompt else self.model_config.system_prompt
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
        # priority = 4 if fans_medal_level else priority
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