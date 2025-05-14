from blivedm.blivedm.models.open_live import DanmakuMessage,GiftMessage,SuperChatMessage,GuardBuyMessage,RoomEnterMessage
from models import MessageData
from resources import Resources
from ui import WebUI
from utils.utils import get_avatar_base64, message_precheck
import tasks
import logging

logger = logging.getLogger('Muice.Event')

class WebUIEventHandler:
    """
    WebUI事件处理
    """
    def __init__(self, webui:WebUI, danmu, queue, realtimechat) -> None:
        self.resources = Resources.get()
        self.webui = webui
        self.danmu = danmu
        self.queue = queue
        # self.bot = resource_hub.bot
        self.realtimechat = realtimechat
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
        if self.resources.model.is_running:
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
        if self.resources.captions.connect():
            self.webui.change_captions_status(1)
        else:
            self.webui.ui.notify('无法连接至字幕组件',type='negative')

    def start_realtime_chat(self):
        if self.webui.status.realtime_chat:
            self.webui.ui.notify('不能重复启动！',type='negative')
            return False
        if not self.resources.model.is_running:
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

class DanmuEventHandler:
    """
    弹幕事件处理分发
    """
    def __init__(self, quene, ui:WebUI) -> None:
        self.resources_hub = Resources.get()
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
        if not all((self.resources_hub.model.is_running, self.resources_hub.captions.is_connecting, message_precheck(message))):
            return
        userface = await get_avatar_base64(userface + '@250x250')

        data = MessageData(username, userid, userface, message)
        task_cls, priority = tasks.CommandTask.get_task(message)
        task = task_cls(data)
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
        task = tasks.GiftTask(data)
        await self.quene.put(3, task)

    async def SuperChatEvent(self, superchat:SuperChatMessage):
        username = superchat.uname
        userid = superchat.open_id
        message = superchat.message
        userface = superchat.uface
        rmb = float(superchat.rmb)
        userface = await get_avatar_base64(userface + '@250x250')
        data = MessageData(username, userid, userface, message, total_value=rmb)
        task = tasks.SuperChatTask(data)
        await self.quene.put(1, task)

    async def GuardBuyEvent(self, message:GuardBuyMessage):
        username = message.user_info.uname
        userid = message.user_info.open_id
        guard_level = message.guard_level
        price = message.price / 1000
        data = MessageData(username=username, userid=userid, guard_level=guard_level, total_value=price)
        task = tasks.BuyGuardTask(data)
        await self.quene.put(1, task)

    async def EnterRoomEvent(self, message:RoomEnterMessage):
        username = message.uname
        data = MessageData(username=username)
        task = tasks.EnterRoomTask(data)
        await self.quene.put(10, task)