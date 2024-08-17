from blivedm import blivedm
from blivedm.blivedm.models import open_live as open_models
from blivedm.blivedm.models import web as web_models
import logging,asyncio,threading

logger = logging.getLogger(__name__)

class DanmuHandler(blivedm.BaseHandler):
    def __init__(self, uilog):
        self.uilog = uilog

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        logging.debug(f'[{client.room_id}] 心跳')

    def _on_open_live_danmaku(self, client: blivedm.OpenLiveClient, message: open_models.DanmakuMessage):
        logging.info(f'{message.uname}：{message.msg}')
        self.uilog.push(f'{message.uname}：{message.msg}')

    def _on_open_live_gift(self, client: blivedm.OpenLiveClient, message: open_models.GiftMessage):
        coin_type = '金瓜子' if message.paid else '银瓜子'
        total_coin = message.price * message.gift_num
        logger.info(f'{message.uname} 赠送{message.gift_name}x{message.gift_num}'
              f' （{coin_type}x{total_coin}）')

    def _on_open_live_buy_guard(self, client: blivedm.OpenLiveClient, message: open_models.GuardBuyMessage):
        logger.info(f'{message.user_info.uname} 购买 大航海等级={message.guard_level}')

    def _on_open_live_super_chat(
        self, client: blivedm.OpenLiveClient, message: open_models.SuperChatMessage
    ):
        logger.info(f'醒目留言 ¥{message.rmb} {message.uname}：{message.message}')
        self.uilog.push(f'醒目留言 ¥{message.rmb} {message.uname}：{message.message}')

class Danmu:
    def __init__(self,config,uilog,status):
        self.config = config
        self.uilog = uilog
        self.status = status
        self.__client_process = False
        self.loop = None

    async def __run_client(self):
        self.__client_process = True
        self.client = blivedm.OpenLiveClient(
            access_key_id = self.config.DANMU_ACCESS_KEY_ID,
            access_key_secret = self.config.DANMU_ACCESS_KEY_SECRET,
            app_id = self.config.DANMU_APP_ID,
            room_owner_auth_code = self.config.DANMU_ROOM_OWNER_AUTH_CODE,
        )
        handler = DanmuHandler(self.uilog)
        self.client.set_handler(handler)
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

    async def start_client(self):
        client_thread = threading.Thread(target=self.__start_client)
        client_thread.start()
        self.status.change_blivedm_status(1)

    async def close_client(self):
        self.__client_process = False
        await asyncio.sleep(1)
        self.status.change_blivedm_status(0)