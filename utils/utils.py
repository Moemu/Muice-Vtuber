import sys
import os
import asyncio
import shlex
import pyaudio
import wave
import requests
import base64
import emoji

async def run_command(command: str, log: object, cwd: str = os.path.dirname(os.path.abspath(__file__))) -> None:
    command = command.replace('python3', sys.executable)
    process = await asyncio.create_subprocess_exec(
        *shlex.split(command, posix='win' not in sys.platform.lower()),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        cwd=cwd
    )
    output = ""
    while True:
        new = await process.stdout.read(4096)
        if not new:
            break
        try:
            new_decode = new.decode('utf-8')
        except UnicodeDecodeError:
            new_decode = new.decode('gbk')
        output += new_decode
        log.push(new_decode)

def get_audio_output_devices_index():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        device = p.get_device_info_by_index(i)
        if device.get('maxOutputChannels') > 0:
            print(device.get('index'),device.get('name'))

def play_audio(file_path:str = './log/output.wav'):
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
    while data:
        stream.write(data)
        data = wf.readframes(1024)

    # 停止并关闭流
    stream.stop_stream()
    stream.close()
    wf.close()
    p.terminate()

def get_avatar_base64(url:str) -> str:
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    return base64.b64encode(response.content).decode("ascii")

def message_precheck(message:str) -> str:
    return message.startswith('!') or message.startswith('#') or (message.startswith('[') and message.endswith(']')) or emoji.emoji_count(message) == len(message)


class Captions:
    def __init__(self) -> None:
        self.captions_server = 'http://127.0.0.1:5500/api/sendmessage'
        self.is_connecting = False

    def connect(self) -> bool:
        try:
            requests.get(self.captions_server)
            self.is_connecting = True
            return True
        except:
            return False
        
    def post(self, message:str, username:str, userface:str, respond:str, leisure:bool = False) -> bool:
        if leisure:
            data = {'user':'', 'avatar':'', 'message':'', 'respond':respond}
        else:
            data = {'user':username, 'avatar':userface, 'message':message, 'respond':respond}
        result = requests.post(self.captions_server, json = data)
        if result.status_code == 200:
            return True