from event import DanmuEventHandler, WebUIEventHandler, EventQueue, LeisureTask
from danmu import Danmu, DanmuHandler
from ui import WebUI
from utils.logger import init_logger
from _types import *
# from qqbot import BotApp
from realtime_chat import RealtimeChat
import signal
import logging
import sys
import threading
# import requests

import warnings
warnings.filterwarnings("ignore", message="`torch.distributed.reduce_op` is deprecated")

class App:
    def __init__(self):
        self.logger = init_logger(logging.DEBUG)
        self.logger.info('初始化应用程序...')
        self.ui = WebUI()
        self.resource_hub = ResourceHub.load_resource()
        self.leisuretask = LeisureTask(self.resource_hub)
        self.queue = EventQueue()
        self.queue.leisure_task = self.leisuretask
        self.realtime_chat = RealtimeChat(self.resource_hub)
        self.event_handler = DanmuEventHandler(self.resource_hub, self.queue, self.ui)
        self.danmu_handler = DanmuHandler(self.event_handler)
        self.danmu = Danmu(self.resource_hub, self.danmu_handler, self.ui)
        self.web_ui_event_handler = WebUIEventHandler(self.resource_hub, self.ui, self.danmu, self.queue, self.realtime_chat)
        self.ui.action = self.web_ui_event_handler
        self.danmu.webui = self.ui
        self.web_ui_event_handler.webui = self.ui
        self.web_ui_event_handler.danmu = self.danmu

        signal.signal(signal.SIGINT, self.shutdown)
        threading.excepthook = self.error

    def start(self):
        try:
            self.logger.info("WebUI运行地址: http://localhost:8081")
            self.ui.start()
        except Exception as e:
            self.logger.error(f"加载WebUI时出现了问题: {e}", exc_info=True)

    def error(self, args):
        self.logger.error(f"线程 {args.thread.name} 发生了一个错误", exc_info=True)
        self.queue.stop()
        self.danmu.close_client()
        self.logger.warning(f"消息处理已暂停，blivedm已安全断开")
        # if self.bot.is_started:
        #     requests.post('http://localhost:8083/live_error')

    def shutdown(self, signum, frame):
        self.resource_hub.model.is_running = False
        if self.queue.is_running:
            self.queue.stop()
        self.danmu.close_client()
        self.resource_hub.captions.disconnect()
        self.ui.app.shutdown()
        sys.exit(0)

if __name__ in {"__main__", "__mp_main__"}:
    app = App()
    app.start()