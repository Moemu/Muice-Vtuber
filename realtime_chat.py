import numpy as np
import wave
import logging
import os
import keyboard
import asyncio
from config import Config
from custom_types import BasicModel
from tts import EdgeTTS
from sqlite import Database
from llm.utils.memory import generate_history
from utils.utils import play_audio,Captions
from utils.audio_process import SpeechRecognitionPipeline
import threading
import pyaudio

logger = logging.getLogger('Muice.RealtimeChat')

class RealtimeChat:
    def __init__(self, model: BasicModel, tts: EdgeTTS, caption: Captions = None):
        self.CHUNK = 2048  # 每次读取的音频块大小
        self.FORMAT = pyaudio.paInt32  # 音频格式
        self.CHANNELS = 2  # 声道数
        self.RATE = 44100  # 采样率
        self.THRESHOLD = 75  # 音量阈值
        self.SILENCE_THRESHOLD_MS = 1500  # 静音阈值
        self.SILENCE_COUNT = int(self.SILENCE_THRESHOLD_MS / (1000 * self.CHUNK / self.RATE))  # 静音计数阈值
        self.use_virtual_device = False  # 是否使用虚拟音频设备
        self.device_index = 1 if not self.use_virtual_device else 3  # 音频设备索引
        self.p = pyaudio.PyAudio()
        self.frames = []
        self.configs = Config().config
        self.audio_name_or_path = self.configs['realtime']['path']
        self.database = Database()
        self.model = model
        self.tts = tts
        self.caption = caption
        self.is_recording = False
        self.model_status = False
        self.first_run = True
        if not os.path.exists('./audio_tmp'):
            os.makedirs('./audio_tmp')
        self.stream = None

    def __load(self):
        self.stream = self.p.open(format=self.FORMAT,
                                  channels=self.CHANNELS,
                                  rate=self.RATE,
                                  input=True,
                                  frames_per_buffer=self.CHUNK,
                                  input_device_index=self.device_index)
        SpeechRecognitionPipeline.load_model(self.audio_name_or_path)
        self.model_status = True

    def save_wav(self, frames, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(self.FORMAT))
            wf.setframerate(self.RATE)
            wf.writeframes(b''.join(frames))

    def start_record(self):
        if not self.is_recording:
            self.is_recording = True
            self.frames = []
            self.stream = self.p.open(format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                input_device_index=self.device_index)
            
            # 开启录音线程
            self.recording_thread = threading.Thread(target=self.record, name='recording_thread', daemon=True)
            self.recording_thread.start()
            logger.info('开始录音')

    def record(self):
        """ 录音逻辑，运行在独立线程 """
        while self.is_recording:
            data = self.stream.read(self.CHUNK)
            self.frames.append(data)
        logger.info("录音线程结束")
        
    def stop_record(self):
        if self.is_recording:
            self.is_recording = False
            self.recording_thread.join()

            self.stream.stop_stream()
            self.stream.close()
            self.save_wav(self.frames, "./temp/stt_output.wav")
            logger.info('结束录音')
    
    async def generate_reply(self):
        logger.info(f"已保存音频文件，开始语音处理")
        message = await SpeechRecognitionPipeline().generate_speech("./temp/stt_output.wav") # 语音识别输出用户Prompt
        if len(message) < 2:
            return
        os.remove("./temp/stt_output.wav")
        memory = generate_history(message, self.database.get_history(), '<RealtimeChat>')
        reply = self.model.ask(prompt=message, history=memory)
        self.database.add_item("<RealtimeChat>", "0", message, reply)
        self.caption.post(message, '沐沐', '', reply)
        logger.info(f"回复消息：{reply}")
        try:
            if self.tts.speak(reply):
                play_audio()
        except Exception as e:
            logger.error(f"播放语音文件失败: {e}")
        logger.info("当前对话结束.")
        
        logger.info("录音结束.")
        self.stream.stop_stream()
        self.stream.close()
        # self.p.terminate()

    def toggle_recording(self):
        """ 切换录音状态 """
        if not self.model_status:
            self.__load()
        if self.is_recording:
            self.stop_record()
            asyncio.run(self.generate_reply())
        else:
            self.start_record()

    def register_keyboard(self):
        keyboard.add_hotkey('ctrl+alt+c', self.toggle_recording)

    def unregister_keyboard(self):
        keyboard.remove_hotkey('ctrl+alt+c')
        if self.is_recording:
            self.stop_record()
        

if __name__ == '__main__':
    from llm import spark
    from tts import EdgeTTS
    model = spark.llm()
    tts = EdgeTTS()
    config = Config()
    model.load(config.LLM_MODEL_PATH, config.LLM_ADAPTER_PATH, config.LLM_SYSTEM_PROMPT, config.LLM_AUTO_SYSTEM_PROMPT, config.LLM_EXTRA_ARGS)
    chat = RealtimeChat(model, tts)
    chat.register_keyboard()
    logger.info("实时聊天已启动，按下Ctrl+Alt+C开始/结束录音")
    keyboard.wait()