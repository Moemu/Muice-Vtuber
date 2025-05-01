from utils.utils import Captions
from config import Config, get_model_config
from abc import abstractmethod, ABC
from llm import BasicModel
from sqlite import Database
from typing import Type, Optional
# from utils.filter import message_filiter
from dataclasses import dataclass
from plugin import get_tools
import importlib
import wave
import pyaudio
import asyncio
import logging
import time

logger = logging.getLogger("Muice.types")

def _load_model(model_config_types:str = "default") -> BasicModel:
    """
    初始化模型类
    """
    model_config = get_model_config(model_config_types = model_config_types)
    module_name = f"llm.{model_config.loader}"
    module = importlib.import_module(module_name)
    ModelClass:Type[BasicModel]|None = getattr(module, model_config.loader, None)
    if not ModelClass: raise ValueError(f"Model {model_config.loader} Not Found!")
    model = ModelClass(model_config)
    model.load()
    return model

class BasicTTS(ABC):
    def __init__(self):
        self.is_playing = False
        
    @abstractmethod
    async def generate_tts(self, text:str) -> Optional[str]:
        """
        生成 TTS 语音文件
        """
        pass

    async def play_audio(self, file_path:str = './temp/tts_output.wav'):
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
            # 让出控制权给其他协程
            await asyncio.sleep(0.01)

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

        model = _load_model()
        leisure_model = _load_model("leisure")
        multimodal = _load_model("multimodal")

        captions = Captions()
        database = Database()
        return ResourceHub(config, model, leisure_model, multimodal, tts, captions, database)

@dataclass(frozen=True)
class MessageData:
    """提取后的消息体"""
    username: str = ""
    """用户名"""
    userid: str = ""
    """用户B站ID"""
    userface: str = ""
    """用户头像"""

    message: str = ""
    """弹幕消息"""

    gift_name: str = ""
    """礼物名称"""
    gift_num: int = 0
    """礼物数量"""
    total_value: float = 0
    """总价值（rmb）"""
    guard_level: int = 0
    """大航海等级"""

    fans_medal_level: int = 0
    """粉丝牌等级"""

# 任务处理基类
class BasicTask(ABC):
    '''基本任务'''
    def __init__(self, resource_hub: ResourceHub, data:MessageData) -> None:
        self.resource_hub = resource_hub
        self.model = resource_hub.model
        self.model_config = self.model.config
        self.leisure_model = resource_hub.leisure_model
        self.multimodal = resource_hub.multimodal
        self.tts = resource_hub.tts
        self.captions = resource_hub.captions
        self.database = resource_hub.database
        self.data = data

        self.tools = get_tools() if self.model_config.function_call else []
        self.time = time.time()
        
        self.response: str = ""
        self.tts_file: Optional[str] = None
        self.is_saved: bool = False
        """是否已经保存到数据库或是不需要保存"""

    def __lt__(self, other):
        return id(self) < id(other)
    
    # def __str__(self) -> str:
    #     return "<>"
    
    # @staticmethod
    # def message_filter(func):
    #     @functools.wraps(func)
    #     async def wrapper(self, *args, **kwargs):
    #         if message_filiter(self.data.message):
    #             return await func(self, *args, **kwargs)
    #         logger.warning(f"{self.data.message} 在消息预检时被过滤")
    #         await self.post_response(self, "(已过滤)。啊这...要不要我们换一个话题聊？qwq", False)
    #     return wrapper

    @abstractmethod
    async def pretreatment(self) -> bool:
        """
        消息预处理（缓存队列）
        """
        pass

    async def post_response(self):
        """
        在直播间输出结果
        """
        if self.tts_file is None:
            logger.warning("不存在 tts 输出！该任务不执行")
            return

        if self.data.message:
            await self.captions.post(
                self.data.message, 
                self.data.username, 
                self.data.userface, 
                self.response
            )
        else:
            await self.captions.post(respond=self.response)

        await self.tts.play_audio(self.tts_file)

        if not self.is_saved:
            await self.database.add_item(
                self.data.username, 
                self.data.userid, 
                self.data.message, 
                self.response
            )