from abc import abstractmethod, ABC
from typing import Optional
import wave
import pyaudio
import asyncio

class BaseTTS(ABC):
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