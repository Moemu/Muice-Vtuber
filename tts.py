import asyncio
import edge_tts
import threading
import logging
import os
import requests

from pydub import AudioSegment
from custom_types import BasicTTS

logger = logging.getLogger('Muice.TTS')

class EdgeTTS(BasicTTS):
    def __init__(self, config:dict) -> None:
        self.__VOICE = "zh-CN-XiaoyiNeural"
        self.__OUTPUT_FILE = "./temp/tts_output.wav"
        self.text = None
        self.result = True

    async def __run(self) -> None:
        communicate = edge_tts.Communicate(self.text, self.__VOICE, proxy='http://127.0.0.1:7890')
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
        
        # 如果生成的mp3文件为空，说明出现了问题
        if os.stat(self.__OUTPUT_FILE.replace('wav', 'mp3')).st_size == 0:
            self.result = False
            logger.warning("生成的TTS语音文件为空")
            return
        
        sound = AudioSegment.from_mp3(self.__OUTPUT_FILE.replace('wav', 'mp3'))
        sound.export(self.__OUTPUT_FILE, format="wav")

    def generate_tts(self, text) -> bool:
        self.text = text
        client_thread = threading.Thread(target=self.__speak, name='EdgeTTS_Speak', daemon=True)
        client_thread.start()
        client_thread.join()
        return self.result
    

class GPTSoVITS(BasicTTS):
    def __init__(self, config: dict):
        """
        初始化 TTS 类，配置服务器地址、端口和配置文件路径。
        
        :param config: 配置字典
        """
        self.host = config.get('host', '127.0.0.1')
        self.port = config.get('port', 9880)
        self.config_path = config.get('config_path', 'GPT_SoVITS/configs/tts_infer.yaml')
        self.base_url = f'http://{self.host}:{self.port}'

        self.ref_audio_path = config.get('ref_audio_path', None)
        self.prompt_text = config.get('prompt_text', "")
        self.prompt_lang = config.get('prompt_lang', "zh")

        self.text_split_method = config.get('text_split_method', "cut5")
        self.batch_size = config.get('batch_size', 1)
        self.media_type = config.get('media_type', "wav")
        self.streaming_mode = config.get('streaming_mode', False)
        self.top_k = config.get('top_k', 5)
        self.top_p = config.get('top_p', 1)
        self.temperature = config.get('temperature', 1)
        self.speed_factor = config.get('speed_factor', 1.0)
        self.seed = config.get('seed', -1)
        self.parallel_infer = config.get('parallel_infer', False)
        self.repetition_penalty = config.get('repetition_penalty', 1.35)

    
    def generate_tts(self, text, text_lang='zh', ref_audio_path=None, prompt_text="", prompt_lang="zh"):
        """
        进行 TTS 推理请求，生成音频流。

        :param text: 输入的文本内容
        :param text_lang: 文本的语言，例如 "zh"
        :param ref_audio_path: 参考音频文件路径
        :param prompt_text: 提示文本，默认为空
        :param prompt_lang: 提示文本语言，默认为 "zh"

        :return: 返回生成的音频流（wav 格式）
        """
        url = f'{self.base_url}/tts'

        if not ref_audio_path:
            ref_audio_path = self.ref_audio_path
        if not prompt_text:
            prompt_text = self.prompt_text
        if not prompt_lang:
            prompt_lang = self.prompt_lang
        
        # 准备POST请求的参数
        payload = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_lang": prompt_lang,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "text_split_method": self.text_split_method,
            "batch_size": self.batch_size,
            "media_type": self.media_type,
            "streaming_mode": self.streaming_mode,
            "speed_factor": self.speed_factor,
            "seed": self.seed,
            "parallel_infer": self.parallel_infer,
            "repetition_penalty": self.repetition_penalty
        }
        
        try:
            # 发起POST请求进行推理
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                audio_data = response.content  # 返回音频流
                self.__save_wav(audio_data)  # Save the audio to a WAV file
                return audio_data
            else:
                print(f"请求失败: {response.status_code}, 错误信息: {response.json()}")
                return None
        except Exception as e:
            print(f"请求过程中出现异常: {e}")
            return None
    
    def control_server(self, command):
        """
        向控制接口发送命令，重新启动或退出服务器。

        :param command: 控制命令，可选 'restart' 或 'exit'
        :return: 无返回值，成功或失败取决于服务器响应
        """
        url = f'{self.base_url}/control'
        payload = {"command": command}
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                print("命令执行成功")
            else:
                print(f"命令执行失败: {response.status_code}, 错误信息: {response.json()}")
        except Exception as e:
            print(f"控制命令请求过程中出现异常: {e}")
    
    def set_gpt_weights(self, weights_path):
        """
        切换GPT模型的权重。

        :param weights_path: 权重文件路径
        :return: 无返回值，成功或失败取决于服务器响应
        """
        url = f'{self.base_url}/set_gpt_weights'
        params = {"weights_path": weights_path}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                print("GPT模型权重切换成功")
            else:
                print(f"切换失败: {response.status_code}, 错误信息: {response.json()}")
        except Exception as e:
            print(f"切换GPT模型过程中出现异常: {e}")
    
    def set_sovits_weights(self, weights_path):
        """
        切换SoVits模型的权重。

        :param weights_path: 权重文件路径
        :return: 无返回值，成功或失败取决于服务器响应
        """
        url = f'{self.base_url}/set_sovits_weights'
        params = {"weights_path": weights_path}
        
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                print("SoVits模型权重切换成功")
            else:
                print(f"切换失败: {response.status_code}, 错误信息: {response.json()}")
        except Exception as e:
            print(f"切换SoVits模型过程中出现异常: {e}")

    def __save_wav(self, audio_data, file_path="./temp/tts_output.wav"):
        with open(file_path, 'wb') as f:
            f.write(audio_data)