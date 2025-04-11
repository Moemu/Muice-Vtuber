import wave
import logging
import os
import keyboard
import asyncio
from config import Config
from _types import ResourceHub, MessageData
from event import EventQueue, DevMicrophoneTask
from sqlite import Database
from utils.audio_process import SpeechRecognitionPipeline
import threading
import pyaudio

logger = logging.getLogger('Muice.RealtimeChat')

CHUNK = 2048  # 每次读取的音频块大小
FORMAT = pyaudio.paInt32  # 音频格式
CHANNELS = 2  # 声道数
RATE = 44100  # 采样率
THRESHOLD = 75  # 音量阈值
SILENCE_THRESHOLD_MS = 1500  # 静音阈值
SILENCE_COUNT = int(SILENCE_THRESHOLD_MS / (1000 * CHUNK / RATE))  # 静音计数阈值
device_index = 1

class RealtimeChat:
    def __init__(self, resource_hub: ResourceHub, queue:EventQueue):
        self.queue = queue
        self.resource_hub = resource_hub

        self.p = pyaudio.PyAudio()
        self.frames = []
        self.configs = Config().config
        self.audio_name_or_path = self.configs['realtime']['path']
        self.database = Database()

        self.is_recording = False
        self.model_status = False
        self.first_run = True
        if not os.path.exists('./audio_tmp'):
            os.makedirs('./audio_tmp')
        self.stream = None
        

    def __load(self):
        self.stream = self.p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  frames_per_buffer=CHUNK,
                                  input_device_index=device_index)
        SpeechRecognitionPipeline.load_model(self.audio_name_or_path)
        self.model_status = True

    def save_wav(self, frames, filename):
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.p.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))

    def start_record(self):
        if not self.is_recording:
            self.is_recording = True
            self.frames = []
            self.stream = self.p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=device_index)
            
            # 开启录音线程
            self.recording_thread = threading.Thread(target=self.record, name='recording_thread', daemon=True)
            self.recording_thread.start()
            logger.info('开始录音')

    def record(self):
        """ 录音逻辑，运行在独立线程 """
        while self.is_recording and self.stream:
            data = self.stream.read(CHUNK)
            self.frames.append(data)
        logger.info("录音线程结束")
        
    def stop_record(self):
        if self.is_recording and self.stream:
            self.is_recording = False
            self.recording_thread.join()

            self.stream.stop_stream()
            self.stream.close()
            self.save_wav(self.frames, "./temp/stt_output.wav")
            logger.info('结束录音')
    
    async def generate_reply(self):
        logger.info(f"已保存音频文件，开始语音处理")
        message = await SpeechRecognitionPipeline().generate_speech("./temp/stt_output.wav") # 语音识别输出用户Prompt
        if not message or len(message) < 2: return
        os.remove("./temp/stt_output.wav")

        data = MessageData(username="沐沐", message=message, userid="0")
        task = DevMicrophoneTask(self.resource_hub, data)
        await self.queue.put(1, task)

        logger.info("录音结束.")
        if self.stream:
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