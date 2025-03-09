from utils.utils import Captions
from sqlite import Database
from config import Config
from abc import abstractmethod
import importlib
import wave
import pyaudio

class BasicModel:
    def __init__(self, config:dict) -> None:
        self.is_running = False

    @abstractmethod
    def load(self, model_config:dict):
        '''加载模型'''
        pass

    @abstractmethod
    def ask(self, prompt:str, history:list) -> str:
        """
        模型交互询问
        """
        pass

    def query_image(self, image_path:str) -> str:
        """
        查询图片
        """
        raise NotImplementedError("当前模型不支持图片识别！")


class BasicTTS:
    def __init__(self):
        self.is_playing = False
        
    @abstractmethod
    def generate_tts(self, text:str) -> bool:
        '''生成TTS语音文件'''
        pass

    def play_audio(self, file_path:str = './temp/tts_output.wav'):
        self.is_playing = True

        wf = wave.open(file_path, 'rb')
        p = pyaudio.PyAudio()

        # 打开音频流
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True,
                        output_device_index=7)

        # 读取音频文件并播放
        data = wf.readframes(1024)
        while data and self.is_playing:
            stream.write(data)
            data = wf.readframes(1024)

        # 停止并关闭流
        stream.stop_stream()
        stream.close()
        wf.close()
        p.terminate()
        self.is_playing = False

class ResourceHub:
    def __init__(self, config:Config, model:BasicModel, leisure_model:BasicModel, multimodal:BasicModel, tts:BasicTTS, captions:Captions, database:Database) -> None:
        self.config = config
        self.model = model
        self.leisure_model = leisure_model
        self.multimodal = multimodal
        self.tts = tts
        self.captions = captions
        self.database = database

    @staticmethod
    def load_resource():
        config = Config()
        tts_module = importlib.import_module(f"tts")
        tts = getattr(tts_module, config.TTS_LOADER)(config.TTS_CONFIG)
        model = importlib.import_module(f"llm.{config.LLM_MODEL_LOADER}").llm()
        leisure_model = importlib.import_module(f"llm.{config.LEISURE_MODEL_LOADER}").llm()
        leisure_model.load(config.LEISURE_MODEL_CONFIG)
        multimodal = importlib.import_module(f"llm.{config.MULTIMODAL_MODEL_LOADER}").llm()
        multimodal.load(config.MULTIMODAL_MODEL_CONFIG)
        captions = Captions()
        database = Database()
        return ResourceHub(config, model, leisure_model, multimodal, tts, captions, database)
    
# 任务处理基类
class BasicTask:
    '''基本任务'''
    def __init__(self, resource_hub: ResourceHub, data:dict = {}) -> None:
        self.resource_hub = resource_hub
        self.model = resource_hub.model
        self.leisure_model = resource_hub.leisure_model
        self.multimodal = resource_hub.multimodal
        self.tts = resource_hub.tts
        self.captions = resource_hub.captions
        self.database = resource_hub.database
        self.data = data

    def __lt__(self, other):
        return id(self) < id(other)
    
    def run(self):
        '''基本任务运行入口'''
        pass