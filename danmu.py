from blivedm import blivedm
from blivedm.blivedm.models import open_live as open_models
from blivedm.blivedm.models import web as web_models
from event import EventHandler
import logging,asyncio,threading,time

logger = logging.getLogger('Muice.Danmu')

class DanmuHandler(blivedm.BaseHandler):
    def __init__(self, EventHandler:EventHandler):
        self.EventHandler = EventHandler

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        # logger.debug(f"心跳: {message}")
        pass

    def _on_open_live_danmaku(self, client: blivedm.OpenLiveClient, message: open_models.DanmakuMessage):
        self.EventHandler.DanmuEvent(message)

    def _on_open_live_gift(self, client: blivedm.OpenLiveClient, message: open_models.GiftMessage):
        self.EventHandler.GiftEvent(message)

    def _on_open_live_buy_guard(self, client: blivedm.OpenLiveClient, message: open_models.GuardBuyMessage):
        self.EventHandler.GuardEvent(message)

    def _on_open_live_super_chat(
        self, client: blivedm.OpenLiveClient, message: open_models.SuperChatMessage
    ):
        self.EventHandler.SuperChatEvent(message)

class Danmu:
    def __init__(self,config,danmuhandler,webui = None):
        self.config = config
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
        client_thread = threading.Thread(target=self.__start_client, daemon=True)
        client_thread.start()
        self.webui.change_blivedm_status(1)

    def close_client(self):
        self.__client_process = False
        time.sleep(1)
        self.webui.change_blivedm_status(0)