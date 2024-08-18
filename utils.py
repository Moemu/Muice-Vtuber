import sys
import os
import asyncio
import shlex
import pyaudio
import wave

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
                    output_device_index=8)

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