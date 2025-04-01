from blivedm import blivedm
from blivedm.blivedm.models import open_live as open_models
from blivedm.blivedm.models import web as web_models
from event import DanmuEventHandler
import logging,asyncio,threading,time

logger = logging.getLogger('Muice.Danmu')

class DanmuHandler(blivedm.BaseHandler):
    def __init__(self, EventHandler:DanmuEventHandler):
        self.EventHandler = EventHandler

    def on_client_stopped(self, client, exception):
        self.EventHandler.shutdown()
    
    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        # logger.debug(f"心跳: {message}")
        pass

    def _on_open_live_enter_room(self, client: blivedm.OpenLiveClient, message: open_models.RoomEnterMessage):
        """进入房间"""
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self.EventHandler.EnterRoomEvent(message), loop)

    def _on_open_live_danmaku(self, client: blivedm.OpenLiveClient, message: open_models.DanmakuMessage):
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self.EventHandler.DanmuEvent(message), loop)

    def _on_open_live_gift(self, client: blivedm.OpenLiveClient, message: open_models.GiftMessage):
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self.EventHandler.GiftEvent(message), loop)

    def _on_open_live_buy_guard(self, client: blivedm.OpenLiveClient, message: open_models.GuardBuyMessage):
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self.EventHandler.GuardBuyEvent(message), loop)

    def _on_open_live_super_chat(
        self, client: blivedm.OpenLiveClient, message: open_models.SuperChatMessage
    ):
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(self.EventHandler.SuperChatEvent(message), loop)

class Danmu:
    def __init__(self, resource_hub, danmuhandler, webui = None):
        self.config = resource_hub.config
        self.__client_process = False
        self.loop = None
        self.handler = danmuhandler
        self.webui = webui

    async def __run_client(self):
        self.__client_process = True
        self.client = blivedm.OpenLiveClient(
            access_key_id = self.config.DANMU_ACCESS_KEY_ID,
            access_key_secret = self.config.DANMU_ACCESS_KEY_SECRET,
            app_id = self.config.DANMU_APP_ID,
            room_owner_auth_code = self.config.DANMU_ROOM_OWNER_AUTH_CODE,
        )
        self.client.set_handler(self.handler)
        self.client.start()
        try:
            while self.__client_process:
                await asyncio.sleep(0.5)
            self.client.stop()
            await self.client.join()
        finally:
            await self.client.stop_and_close()

    def __start_client(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)  # 将事件循环设置为当前线程的默认事件循环
        try:
            self.loop.run_until_complete(self.__run_client())
        finally:
            self.loop.close()

    def start_client(self):
        client_thread = threading.Thread(target=self.__start_client, name='Blivedm', daemon=True)
        client_thread.start()
        if self.webui:
            self.webui.change_blivedm_status(1)

    def close_client(self):
        self.__client_process = False
        time.sleep(1)
        if self.webui:
            self.webui.change_blivedm_status(0)