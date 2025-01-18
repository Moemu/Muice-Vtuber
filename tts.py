import asyncio
import edge_tts
import threading
import logging
from pydub import AudioSegment

logger = logging.getLogger('Muice.TTS')

class EdgeTTS:
    def __init__(self) -> None:
        self.__VOICE = "zh-CN-XiaoyiNeural"
        self.__OUTPUT_FILE = "log/output.wav"
        self.text = None
        self.result = True

    async def __run(self) -> None:
        communicate = edge_tts.Communicate(self.text, self.__VOICE)
        await communicate.save(self.__OUTPUT_FILE.replace('wav', 'mp3'))
    
    def __speak(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.__run())
            self.result = True
        except Exception as e:
            logger.warning(f"尝试生成TTS语音文件时出现了问题: {e}")
            self.result = False
            return
        finally:
            loop.close()
        sound = AudioSegment.from_mp3(self.__OUTPUT_FILE.replace('wav', 'mp3'))
        sound.export(self.__OUTPUT_FILE, format="wav")

    def speak(self,text) -> bool:
        self.text = text
        client_thread = threading.Thread(target=self.__speak)
        client_thread.start()
        client_thread.join()
        return self.result