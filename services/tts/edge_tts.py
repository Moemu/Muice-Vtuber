from ._base import BaseTTS
from pathlib import Path
from typing import Optional
from pydub import AudioSegment
import time
import edge_tts
import logging
import os

logger = logging.getLogger("Muice.tts")

class EdgeTTS(BaseTTS):
    def __init__(self, config:dict) -> None:
        self.__VOICE = "zh-CN-XiaoyiNeural"
        self.__OUTPUT_PATH = Path("./temp/tts")
        self.text = None
        self.result = True

        self.__OUTPUT_PATH.mkdir(exist_ok=True)

    async def generate_tts(self, text:str, proxy:str|None = 'http://127.0.0.1:7890') -> Optional[str]:
        output_file = str(self.__OUTPUT_PATH / f"{time.time_ns()}.mp3")

        try:
            communicate = edge_tts.Communicate(text, self.__VOICE, proxy = proxy)
            await communicate.save(output_file)
        except Exception as e:
            if proxy:
                return await self.generate_tts(text, proxy = None)
            logger.warning(f"尝试生成TTS语音文件时出现了问题: {e}")
            return None

        if os.stat(output_file).st_size == 0:
            logger.warning("生成的TTS语音文件为空")
            return None
        
        sound = AudioSegment.from_mp3(output_file)
        sound.export(output_file.replace(".mp3", ".wav"), format="wav")
        
        return output_file.replace(".mp3", ".wav")