from tts import EdgeTTS
from utils.utils import Captions
from sqlite import Database

class BasicModel:
    def __init__(self):
        self.is_running = False

    def load(self, model_path:str, adapter_path:str, system_prompt:str, auto_system_prompt:bool, extra_args:dict):
        '''加载模型'''
        pass

    def ask(self, prompt:str, history:list) -> str:
        """
        模型交互询问
        """
        pass

# 任务处理基类
class BasicTask:
    '''基本任务'''
    def __init__(self, model:BasicModel, tts:EdgeTTS, captions:Captions, database:Database, data:dict = {}) -> None:
        self.model = model
        self.tts = tts
        self.captions = captions
        self.database = database
        self.data = data

    def __lt__(self, other):
        return id(self) < id(other)
    
    def run(self):
        '''基本任务运行入口'''
        pass