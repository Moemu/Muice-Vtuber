# import sys
# import os
# import asyncio
# import shlex
import pyaudio
import requests
import base64
import emoji
import threading
import logging
import pyautogui
import re
from captions.app import Captions as Captions_app

logger = logging.getLogger('Muice.Utils')


class Captions:
    def __init__(self) -> None:
        self.captions_server = 'http://127.0.0.1:8082/api/sendmessage'
        self.is_connecting = False
        self.app = None
        self.captions_app = None

    def connect(self) -> bool:
        try:
            self.captions_app = Captions_app()
            self.app = threading.Thread(target=self.captions_app.run, name='Captions', daemon=True)
            self.app.start()
            self.is_connecting = True
            logger.info(f"已连接到字幕服务器")
            return True
        except:
            logger.info('连接失败',exc_info=True)
            return False
    
    def disconnect(self) -> bool:
        if not self.captions_app:
            return True
        self.captions_app.socketio.stop()
        self.is_connecting = False
        logger.info(f"已断开字幕服务器")
        return True

    
    def post(self, message:str = '', username:str = '', userface:str = '', respond:str = '') -> bool:
        # data = {'user':username, 'avatar':userface, 'message':message, 'respond':respond}
        data =  {'user':username, 'avatar':userface, 'message':message, 'respond':''}
        result = requests.post(self.captions_server, json=data)
        if result.status_code == 200:
            return True
        return False


# async def run_command(command: str, log: object, cwd: str = os.path.dirname(os.path.abspath(__file__))) -> None:
#     command = command.replace('python3', sys.executable)
#     process = await asyncio.create_subprocess_exec(
#         *shlex.split(command, posix='win' not in sys.platform.lower()),
#         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
#         cwd=cwd
#     )
#     output = ""
#     while True:
#         new = await process.stdout.read(4096)
#         if not new:
#             break
#         try:
#             new_decode = new.decode('utf-8')
#         except UnicodeDecodeError:
#             new_decode = new.decode('gbk')
#         output += new_decode
#         log.push(new_decode)

def get_audio_output_devices_index():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        device = p.get_device_info_by_index(i)
        if device.get('maxOutputChannels') > 0: # type: ignore
            print(device.get('index'),device.get('name'))

def get_avatar_base64(url:str) -> str:
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    return base64.b64encode(response.content).decode("ascii")

def message_precheck(message:str) -> bool:
    # 纯emoji消息不发送
    if emoji.emoji_count(message) == len(message):
        return False
    # B站表情检测
    if message.startswith('[') and message.endswith(']'):
        return False
    # 违禁字符检测
    if '\u200e' in message:
        return False
    # 前缀检测
    return not (message.startswith('＃') or message.startswith('#'))

def screenshot():
    return pyautogui.screenshot('./temp/screenshot.png')

def filter_emotion(text: str) -> str:
    # 定义常见的标点符号
    common_punctuation = r"[.,!?;:()[]{}\"'，。！？；：]"
    # 使用正则表达式去除表情符号和特殊字符
    # 这里的正则表达式去除掉所有非字母、非数字、非常见标点符号的字符
    # text = re.sub(r"[^\w\s" + common_punctuation + "]", "", text)
    # 移除表情
    text = re.sub(r"（[^）]*）", "", text)
    # 移除表情符号 (通过Unicode范围来过滤)
    text = re.sub(r"[^\x00-\x7F\u4e00-\u9fa5]+", "", text)
    text = text.replace('www', '')
    text = text.replace('qwq', '')
    return text

def filter_parentheses(text: str) -> str:
    pattern = r"（.*?）"
    clean_text = re.sub(pattern, "", text)
    return clean_text