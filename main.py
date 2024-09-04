from event import EventHandler,WebUIEventHandler,EventQueue,LeisureTask
from tts import EdgeTTS
from llm import LLMModule
from danmu import Danmu,DanmuHandler
from config import Config
from ui import WebUI
from utils import Captions
from test import Test
from sqlite import Database
import logging

logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = Config()
tts = EdgeTTS()
ui = WebUI()
llm = LLMModule()
captions = Captions()
database = Database()
leisuretask = LeisureTask(llm,tts,captions,database) 
queue = EventQueue()
queue.leisure_task = leisuretask

EventHandler = EventHandler(llm,tts,captions,database,queue,ui)
WebUIEventHandler = WebUIEventHandler(config,llm,captions,queue)
DanmuHandler = DanmuHandler(EventHandler)
test = Test(EventHandler)

danmu = Danmu(config,DanmuHandler)

ui.action = WebUIEventHandler
danmu.webui = ui
WebUIEventHandler.webui = ui
WebUIEventHandler.danmu = danmu
WebUIEventHandler.test = test

if __name__ in {"__main__", "__mp_main__"}:
    ui.start()