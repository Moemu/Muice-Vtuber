from event import DanmuEventHandler, WebUIEventHandler, EventQueue, LeisureTask
from tts import EdgeTTS
from danmu import Danmu, DanmuHandler
from config import Config
from ui import WebUI
from utils.utils import Captions
from test import Test
from sqlite import Database
from utils.logger import init_logger
from qqbot import BotApp
from realtime_chat import RealtimeChat
import signal
import logging
import importlib
import sys
import threading
import requests

DEBUG_MODE = True

class App:
    def __init__(self):
        self.logger = init_logger(logging.DEBUG)
        self.logger.info('初始化应用程序...')

        self.config = Config()
        self.tts = EdgeTTS()
        self.ui = WebUI()
        self.model = importlib.import_module(f"llm.{self.config.LLM_MODEL_LOADER}").llm()
        self.captions = Captions()
        self.database = Database()
        self.leisuretask = LeisureTask(self.model, self.tts, self.captions, self.database)
        self.queue = EventQueue()
        self.queue.leisure_task = self.leisuretask
        self.bot = BotApp(self.model)
        self.realtime_chat = RealtimeChat(self.model, self.tts)

        self.event_handler = DanmuEventHandler(self.model, self.tts, self.captions, self.database, self.queue, self.ui)
        self.web_ui_event_handler = WebUIEventHandler(self.config, self.model, self.captions, self.queue, self.bot, self.realtime_chat)
        self.danmu_handler = DanmuHandler(self.event_handler)
        self.test = Test(self.event_handler)

        self.danmu = Danmu(self.config, self.danmu_handler)

        self.ui.action = self.web_ui_event_handler
        self.danmu.webui = self.ui
        self.web_ui_event_handler.webui = self.ui
        self.web_ui_event_handler.danmu = self.danmu
        self.web_ui_event_handler.test = self.test

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
        if self.bot.is_started:
            requests.post('http://localhost:8083/live_error')

    def shutdown(self, signum, frame):
        self.model.is_running = False
        self.queue.stop()
        self.danmu.close_client()
        self.captions.disconnect()
        self.ui.app.shutdown()
        sys.exit(0)

if __name__ in {"__main__", "__mp_main__"}:
    app = App()
    app.start()