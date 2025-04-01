from blivedm.blivedm.models.open_live import DanmakuMessage,GiftMessage,SuperChatMessage,GuardBuyMessage,RoomEnterMessage
from _types import *
from ui import WebUI
from utils.memory import generate_history
from utils.utils import get_avatar_base64, message_precheck, screenshot, filter_parentheses
import random,asyncio

import logging
logger = logging.getLogger('Muice.Event')

# 任务队列
class EventQueue:
    def __init__(self, first_run=True) -> None:
        self.queue = asyncio.PriorityQueue(maxsize=5)
        if first_run:
            self.leisure_task: LeisureTask | None = None
        self.is_running = False
        self.first_run = first_run
        self.task_index = 1

    async def __run(self):
        idle_time = 0  # 记录空闲的时间
        while self.is_running:
            if self.queue.empty():
                await asyncio.sleep(0.5)  # 仅等待短时间
                
                idle_time += 0.5  # 累积空闲时间
                if idle_time >= 50 and random.random() < 0.1:  # 50s 后才有 10% 概率触发
                    if random.random() < 0.10:
                        logger.info('发布一个读屏任务...')
                        await self.__create_a_read_screen_task()
                    else:
                        logger.info('发布一个闲时任务...')
                        await self.__create_a_leisure_task()
                    idle_time = 0  # 重新计算空闲时间
                continue
            
            idle_time = 0  # 一旦有任务，重置空闲时间
            priority, task_class = await self.queue.get()
            if not task_class: continue

            await task_class.run()  # 执行任务
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
        await self.put(10, ReadScreenTask(self.leisure_task.resource_hub, {}))

    async def put(self, priority:int, event):
        priority += self.task_index
        self.task_index += 1
        await self.queue.put((priority,event))

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
    async def run(self):
        logger.info(f'[{self.data["username"]}]：{self.data["message"]}')
        history = await generate_history(self.resource_hub.database, self.data['message'], self.data['userid'])
        logger.debug(f'[{self.data["username"]}] 获取到的历史记录: {history}')
        
        respond = await self.model.ask(prompt=self.data['message'], history=history, stream=False) or '(已过滤)'
        respond = respond.replace('<USERNAME>', self.data['username'])
        logger.info(f'[{self.data["username"]}] {self.data["message"]} -> {respond}')

        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(self.data['message'], self.data['username'], self.data['userface'], filter_parentheses(respond))
        await self.tts.play_audio()
        await self.database.add_item(self.data['username'], self.data['userid'], self.data['message'], filter_parentheses(respond))

        logger.info(f'[{self.data["username"]}] 事件处理结束')

class GiftTask(BasicTask):
    '''礼物任务'''
    async def run(self):
        logger.info(f'[{self.data["username"]}] 赠送了 {self.data["gift_name"]} x {self.data["gift_num"]} 总价值: {self.data["total_value"]}')
        respond = f"感谢 {self.data['username']} 赠送的 {self.data['gift_name']} 喵，雪雪最喜欢你了喵！"
        logger.info(f'[{self.data["username"]}] {self.data["gift_name"]} -> {respond}')

        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()
        await self.database.add_gift(self.data['username'], self.data['userid'], self.data['gift_name'], self.data['total_value'])

        logger.info(f'[{self.data["username"]}] 事件处理结束')

class SuperChatTask(BasicTask):
    '''醒目留言任务'''
    async def run(self):
        logger.info(f'[{self.data["username"]}] 赠送了 ¥{self.data["rmb"]} 醒目留言：{self.data["message"]}')
        history = await generate_history(self.resource_hub.database, self.data['message'], self.data['userid'])

        model_output = await self.model.ask(self.data['message'], history=history) or '(已过滤)'
        respond = f"感谢 {self.data['username']} 的SuperChat。\n" + model_output
        logger.info(f'[{self.data["username"]}] 醒目留言 -> {respond}')

        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(self.data['message'], self.data['username'], self.data['userface'], respond)
        await self.tts.play_audio()
        await self.database.add_item(self.data['username'], self.data['userid'], f'(¥{self.data["rmb"]}醒目留言)' + self.data['message'], model_output)

        logger.info(f'[{self.data["username"]}] 事件处理结束')

class BuyGuardTask(BasicTask):
    '''上舰任务'''
    async def run(self):
        logger.info(f'{self.data["username"]} 购买了大航海等级 {self.data["guard_level"]}')
        respond = f'感谢 {self.data["username"]} 的舰长喵！会有什么神奇的事情发生呢？'

        logger.info(f'{self.data["username"]} TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()
        await self.database.add_gift(self.data['username'], self.data['userid'], f'大航海等级{self.data["guard_level"]}', self.data['price'])

        logger.info(f'[{self.data["username"]}] 事件处理结束')

class LeisureTask(BasicTask):
    async def run(self):
        # history = self.database.get_history()
        active_prompts = ['<生成推文: 胡思乱想>', '<生成推文: AI生活>', '<生成推文: AI思考>', '<生成推文: 表达爱意>', '<生成推文: 情感建议>']
        prompt = random.choice(active_prompts)

        respond = await self.leisure_model.ask(prompt, history=[])

        await self.database.add_item('闲时任务', '0', prompt, respond)
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()

class EnterRoomTask(BasicTask):
    async def run(self):
        logger.info(f'{self.data["username"]} 进入房间')
        respond = f"欢迎 {self.data['username']} 进入到直播间喵"

        logger.info(f'{self.data["username"]} TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()

        logger.info(f'[{self.data["username"]}] 事件处理结束')

class RefreshTask(BasicTask):
    async def run(self):
        logger.info(f'{self.data["username"]} 请求刷新')
        history = await generate_history(self.resource_hub.database, self.data['message'], self.data['userid'], user_only=True)
        logger.debug(f'获取到的历史记录: {history}')

        prompt = history[-1].danmu
        history = history[:-1]
        respond = await self.model.ask(prompt, history=history) or '(已过滤)'
        logger.info(f'[{self.data["username"]}] {prompt} -> {respond}')

        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(prompt, self.data['username'], self.data['userface'], respond)
        await self.tts.play_audio()
        await self.database.remove_last_item(self.data['userid'])
        await self.database.add_item(self.data['username'], self.data['userid'], prompt, respond)

        logger.info(f'[{self.data["username"]}] 事件处理结束')

class CleanMemoryTask(BasicTask):
    async def run(self):
        logger.info(f'{self.data["username"]} 请求清空对话历史')
        await self.database.unavailable_item(self.data['userid'])
        logger.info(f'{self.data["username"]} 对话历史已清空')
        respond = '对话历史已清空'

        logger.info(f'{self.data["username"]} TTS处理...')
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()

        logger.info(f'[{self.data["username"]}] 事件处理结束')

class ReadScreenTask(BasicTask):
    async def run(self):
        logger.info('[读屏任务] 开始读取屏幕')
        respond = '让我们看一下沐沐在干什么...'
        if not await self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()

        screenshot()
        image_info = await self.multimodal.ask(prompt="用简单的一段话描述一下这张图片", history=[], images=['./temp/screenshot.png'], stream=False)
        respond = await self.model.ask(f'<读屏任务-沐沐的屏幕内容: {image_info}>', history=[]) or '(已过滤)'
        logger.info(f'[读屏任务] <读屏任务-沐沐的屏幕内容: {image_info}> -> {respond}')

        logger.info(f'[读屏任务] TTS处理...')
        if not self.tts.generate_tts(respond): return
        await self.captions.post(respond=respond)
        await self.tts.play_audio()
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
        # self.ui.ui_danmu.push(f'醒目留言 ¥{message.rmb} {message.uname}：{message.message}')
        message = danmu.msg
        username = danmu.uname
        userface = danmu.uface
        userid = danmu.open_id
        if not self.model.is_running or not self.captions.is_connecting or not message_precheck(message):
            return
        userface = await get_avatar_base64(userface + '@250x250')
        data = {'message': message, 'username': username, 'userface': f'data:image/png;base64,' + userface, 'userid': userid}
        if message.startswith('刷新'):
            data = {'message': message, 'username': username, 'userface': userface, 'userid': userid}
            task = RefreshTask(self.resource_hub, data)
            self.quene.put(10, task)
            return
        if message.startswith('清空对话历史'):
            data = {'message': message, 'username': username, 'userface': userface, 'userid': userid}
            task = CleanMemoryTask(self.resource_hub, data)
            self.quene.put(10, task)
            return
        task = DanmuTask(self.resource_hub, data)
        await self.quene.put(5, task)

    async def GiftEvent(self, gift:GiftMessage):
        if not gift.paid:
            return
        username = gift.uname
        userid = gift.open_id
        gift_name = gift.gift_name
        total_value = gift.price * gift.gift_num / 1000
        data = {'username': username, 'userid': userid, 'gift_name': gift_name, 'gift_num': gift.gift_num, 'total_value': total_value}
        task = GiftTask(self.resource_hub, data)
        await self.quene.put(3, task)

    async def SuperChatEvent(self, superchat:SuperChatMessage):
        username = superchat.uname
        userid = superchat.open_id
        message = superchat.message
        userface = superchat.uface
        rmb = superchat.rmb
        userface = await get_avatar_base64(userface + '@250x250')
        data = {'username': username, 'userid': userid, 'userface': f'data:image/png;base64,' + userface, 'message': message, 'rmb': rmb}
        task = SuperChatTask(self.resource_hub, data)
        await self.quene.put(1, task)

    async def GuardBuyEvent(self, message:GuardBuyMessage):
        username = message.user_info.uname
        userid = message.user_info.open_id
        guard_level = message.guard_level
        price = message.price / 1000
        data = {'username': username, 'userid': userid, 'guard_level': guard_level, 'price': price}
        task = BuyGuardTask(self.resource_hub, data)
        await self.quene.put(1, task)

    async def EnterRoomEvent(self, message:RoomEnterMessage):
        username = message.uname
        data = {'username': username}
        task = EnterRoomTask(self.resource_hub, data)
        await self.quene.put(10, task)