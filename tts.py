import asyncio
import edge_tts


class EdgeTTS:
    def __init__(self) -> None:
        self.__VOICE = "zh-CN-XiaoyiNeural"
        self.__OUTPUT_FILE = "log/output.mp3"

    async def speak(self,text) -> None:
        communicate = edge_tts.Communicate(text, self.__VOICE)
        await communicate.save(self.__OUTPUT_FILE)
        return True
    
    def test(self):
        loop = asyncio.get_event_loop_policy().get_event_loop()
        try:
            loop.run_until_complete(self.speak('nihao'))
        finally:
            loop.close()