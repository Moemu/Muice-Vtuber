from event import EventHandler,WebUIEventHandler
from tts import EdgeTTS
from llm import LLMModule
from danmu import Danmu,DanmuHandler
from config import Config
from ui import WebUI
import logging

logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

config = Config()
tts = EdgeTTS()
ui = WebUI()
llm = LLMModule()

EventHandler = EventHandler(llm,tts,ui)
WebUIEventHandler = WebUIEventHandler(config,llm)
DanmuHandler = DanmuHandler(EventHandler)

danmu = Danmu(config,DanmuHandler)

ui.action = WebUIEventHandler
danmu.webui = ui
WebUIEventHandler.webui = ui
WebUIEventHandler.danmu = danmu

if __name__ in {"__main__", "__mp_main__"}:
    ui.start()