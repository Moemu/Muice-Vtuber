import json
import sys
import os
import asyncio
import shlex
import logging

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