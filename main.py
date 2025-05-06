from event import DanmuEventHandler, WebUIEventHandler, PretreatQueue, LeisureTask
from danmu import Danmu, DanmuHandler
from plugin import load_plugins
from ui import WebUI
from utils.logger import init_logger
from _types import *
from resources import Resources
from realtime_chat import RealtimeChat
import signal
import logging
import sys
import threading

logger = init_logger(logging.DEBUG)

class App:
    def __init__(self):
        logger.info('初始化应用程序...')
        Resources.init()

        self.resources = Resources.get()    
        self.ui = WebUI()
        self.leisuretask = LeisureTask(MessageData(username="闲时任务"))
        self.queue = PretreatQueue()
        self.queue.leisure_task = self.leisuretask
        self.realtime_chat = RealtimeChat(self.queue)
        self.event_handler = DanmuEventHandler(self.queue, self.ui)
        self.danmu_handler = DanmuHandler(self.event_handler)
        self.danmu = Danmu(self.danmu_handler, self.ui)
        self.web_ui_event_handler = WebUIEventHandler(self.ui, self.danmu, self.queue, self.realtime_chat)
        self.ui.action = self.web_ui_event_handler
        self.danmu.webui = self.ui
        self.web_ui_event_handler.webui = self.ui
        self.web_ui_event_handler.danmu = self.danmu

        signal.signal(signal.SIGINT, self.shutdown)
        threading.excepthook = self.error

        self._load_plugins()

    def _load_plugins(self):
        load_plugins("./plugins")

    def start(self):
        try:
            logger.info("WebUI运行地址: http://localhost:8081")
            self.ui.start()
        except Exception as e:
            logger.error(f"加载WebUI时出现了问题: {e}", exc_info=True)

    def error(self, args):
        logger.error(f"线程 {args.thread.name} 发生了一个错误", exc_info=True)

        self.queue.stop()
        self.danmu.close_client()

        logger.warning(f"消息处理已暂停，blivedm已安全断开")

    def shutdown(self, signum, frame):
        self.resources.model.is_running = False
        if self.queue.is_running:
            self.queue.stop()
        self.danmu.close_client()
        self.resources.captions.disconnect()
        self.ui.app.shutdown()
        sys.exit(0)

if __name__ in {"__main__", "__mp_main__"}:
    app = App()
    app.start()