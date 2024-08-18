from blivedm.blivedm.models.open_live import DanmakuMessage
from ui import WebUI
from llm import LLMModule, BasicModel
from tts import EdgeTTS
from utils import play_audio
from config import Config

class WebUIEventHandler:
    def __init__(self, config: Config, llm:LLMModule, webui = None, danmu = None) -> None:
        self.config = config
        self.webui = webui
        self.danmu = danmu
        self.llm = llm
        self.model:BasicModel = None
        self.chat_history = []

    def connect_to_LLM(self):
        if self.webui.LLM_status:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        model = self.llm.LoadLLMModule(self.config.LLM_MODEL_LOADER, self.config.LLM_MODEL_PATH, self.config.LLM_ADAPTER_PATH)
        print(model)
        if model:
            self.model = model
            self.webui.change_LLM_status(1)
        else:
            self.webui.ui.notify('无法连接至LLM',type='negative')

    async def connect_to_blivedm(self):
        if self.webui.blivedm_status:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        self.danmu.start_client()

    async def disconnect_to_blivedm(self):
        if not self.webui.blivedm_status:
            self.webui.ui.notify('尚未连接！',type='negative')
            return False
        self.danmu.close_client()

    def chat_with_LLM(self,prompt):
        if self.webui.LLM_status:
            respond = self.model.ask(prompt,self.chat_history)
            self.chat_history.append([prompt,respond])
            return respond
        else:
            self.webui.ui.notify('LLM未连接',type='warning')

class EventHandler:
    def __init__(self, llm:LLMModule, tts:EdgeTTS, ui:WebUI = None) -> None:
        self.llm = llm
        self.tts = tts
        self.ui = ui

    def DanmuEvent(self, danmu:DanmakuMessage):
        self.ui.ui_danmu.push(f'{danmu.uname}：{danmu.msg}')
        # self.ui.ui_danmu.push(f'醒目留言 ¥{message.rmb} {message.uname}：{message.message}')
        message = danmu.msg
        username = danmu.uname
        userface = danmu.uface
        model = self.llm.model
        if model.is_running:
            respond = model.ask(message, history=[])
            self.tts.speak(respond)
            play_audio()
            print(respond)