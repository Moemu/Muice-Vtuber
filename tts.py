import asyncio
import edge_tts
import threading
from pydub import AudioSegment

class EdgeTTS:
    def __init__(self) -> None:
        self.__VOICE = "zh-CN-XiaoyiNeural"
        self.__OUTPUT_FILE = "log/output.wav"
        self.text = None

    async def __run(self) -> None:
        communicate = edge_tts.Communicate(self.text, self.__VOICE)
        await communicate.save(self.__OUTPUT_FILE.replace('wav','mp3'))
        sound = AudioSegment.from_mp3(self.__OUTPUT_FILE.replace('wav','mp3'))
        sound.export(self.__OUTPUT_FILE, format="wav")
        return True
    
    def __speak(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.__run())
        finally:
            loop.close()

    def speak(self,text):
        self.text = text
        client_thread = threading.Thread(target=self.__speak)
        client_thread.start()
        client_thread.join()