from functools import total_ordering
from abc import abstractmethod, ABC
from typing import Optional
# from utils.filter import message_filiter
from dataclasses import dataclass
from plugin import get_tools
import wave
import pyaudio
import asyncio
import logging
import time

logger = logging.getLogger("Muice.types")

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

@dataclass
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

    def __add__(self, other: "MessageData") -> "MessageData":
        self.message += f"。{other.message}"
        return self
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(userid={self.userid}, message={self.message})"

# 任务处理基类
@total_ordering
class BasicTask(ABC):
    '''基本任务'''
    def __init__(self, data:MessageData) -> None:
        from resources import Resources
        self.resources = Resources.get()
        """资源"""
        self.tts = self.resources.tts
        self.model = self.resources.model
        self.captions = self.resources.captions
        self.leisure_model = self.resources.leisure_model
        self.database = self.resources.database
        self.multimodal = self.resources.multimodal

        self.model_config = self.resources.model.config
        """模型配置"""
        self.data = data
        """消息内容"""
        self.tools = get_tools() if self.model_config.function_call else []
        """Function Calls 工具列表"""
        self.time = time.time()
        """事件创建时间"""
        self.response: str = ""
        """模型响应"""
        self.tts_file: Optional[str] = None
        """TTS输出文件路径"""
        self.is_saved: bool = False
        """是否已经保存到数据库或是不需要保存"""

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(time={self.time}, data={self.data})"

    def __lt__(self, other: "BasicTask") -> bool:
        return self.time < other.time
    
    def __eq__(self, other: "BasicTask") -> bool:
        return id(self) == id(other)
    
    def __add__(self, other: "BasicTask") -> "BasicTask":
        self.data += other.data
        return self
    
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
            await self.resources.captions.post(
                self.data.message, 
                self.data.username, 
                self.data.userface, 
                self.response
            )
        else:
            await self.resources.captions.post(respond=self.response)

        await self.resources.tts.play_audio(self.tts_file)

        if not self.is_saved:
            await self.resources.database.add_item(
                self.data.username, 
                self.data.userid, 
                self.data.message, 
                self.response
            )