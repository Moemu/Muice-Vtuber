from event import EventHandler, WebUIEventHandler, EventQueue, LeisureTask
from tts import EdgeTTS
from llm import LLMModule
from danmu import Danmu, DanmuHandler
from config import Config
from ui import WebUI
from utils.utils import Captions
from test import Test
from sqlite import Database
from utils.logging import init_logger
import logging

class App:
    def __init__(self):
        self.logger = init_logger(logging.DEBUG)
        self.logger.info('初始化应用程序...')

        self.config = Config()
        self.tts = EdgeTTS()
        self.ui = WebUI()
        self.llm = LLMModule()
        self.captions = Captions()
        self.database = Database()
        self.leisuretask = LeisureTask(self.llm, self.tts, self.captions, self.database)
        self.queue = EventQueue()
        self.queue.leisure_task = self.leisuretask

        self.event_handler = EventHandler(self.llm, self.tts, self.captions, self.database, self.queue, self.ui)
        self.web_ui_event_handler = WebUIEventHandler(self.config, self.llm, self.captions, self.queue)
        self.danmu_handler = DanmuHandler(self.event_handler)
        self.test = Test(self.event_handler)

        self.danmu = Danmu(self.config, self.danmu_handler)

        self.ui.action = self.web_ui_event_handler
        self.danmu.webui = self.ui
        self.web_ui_event_handler.webui = self.ui
        self.web_ui_event_handler.danmu = self.danmu
        self.web_ui_event_handler.test = self.test

    def start(self):
        try:
            self.logger.info("加载WebUI...")
            self.ui.start()
        except Exception as e:
            self.logger.error(f"加载WebUI时出现了问题: {e}", exc_info=True)

if __name__ in {"__main__", "__mp_main__"}:
    app = App()
    app.start()