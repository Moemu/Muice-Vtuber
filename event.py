from blivedm.blivedm.models.open_live import DanmakuMessage
from ui import WebUI
from llm import LLMModule, BasicModel
from tts import EdgeTTS
from utils import play_audio,Captions
from sqlite import Database
from config import Config

class WebUIEventHandler:
    def __init__(self, config: Config, llm:LLMModule, captions:Captions, webui = None, danmu = None, test = None) -> None:
        self.config = config
        self.webui = webui
        self.danmu = danmu
        self.llm = llm
        self.captions = captions
        self.test = test
        self.model:BasicModel = None
        self.chat_history = []

    def connect_to_LLM(self):
        if self.webui.status.llm:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        model = self.llm.LoadLLMModule(self.config.LLM_MODEL_LOADER, self.config.LLM_MODEL_PATH, self.config.LLM_ADAPTER_PATH)
        if model:
            self.model = model
            self.webui.change_LLM_status(1)
        else:
            self.webui.ui.notify('无法连接至LLM',type='negative')

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
        if self.captions.connect():
            self.webui.change_captions_status(1)
        else:
            self.webui.ui.notify('无法连接至字幕组件',type='negative')

    def chat_with_LLM(self,prompt):
        if self.webui.LLM_status:
            respond = self.model.ask(prompt,self.chat_history)
            self.chat_history.append([prompt,respond])
            return respond
        else:
            self.webui.ui.notify('LLM未连接',type='warning')

    def CreateATestDanmuEvent(self):
        self.test.CreateADanmuEvent()

class EventHandler:
    def __init__(self, llm:LLMModule, tts:EdgeTTS, captions:Captions, database:Database, ui:WebUI = None) -> None:
        self.llm = llm
        self.tts = tts
        self.captions = captions
        self.database = database
        self.ui = ui

    def DanmuEvent(self, danmu:DanmakuMessage):
        self.ui.ui_danmu.push(f'{danmu.uname}：{danmu.msg}')
        # self.ui.ui_danmu.push(f'醒目留言 ¥{message.rmb} {message.uname}：{message.message}')
        message = danmu.msg
        username = danmu.uname
        userface = danmu.uface
        model = self.llm.model
        if not model.is_running and not self.captions.is_connecting:
            return
        history = self.database.get_history()
        respond = model.ask(message, history=history)
        self.database.add_item(username, danmu.open_id, message, respond)
        self.tts.speak(respond)
        self.captions.post(message, username, userface, respond)
        play_audio()