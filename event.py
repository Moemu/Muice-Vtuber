from blivedm.blivedm.models.open_live import DanmakuMessage
from ui import WebUI
from llm import LLMModule, BasicModel
from llm.utils.memory import generate_history
from tts import EdgeTTS
from utils.utils import play_audio,Captions, get_avatar_base64, message_precheck
from config import Config
from sqlite import Database
import queue,threading,time,random

import logging
logger = logging.getLogger('Muice.Event')

# 任务队列
class EventQueue:
    def __init__(self, first_run = True) -> None:
        self.queue = queue.PriorityQueue(maxsize=5)
        self.threading = threading.Thread(target=self.__run)
        self.timer = threading.Timer(60, self.__create_a_leisure_task, ())
        self.leisure_task:LeisureTask = None
        self.is_running = False
        self.first_run = first_run
        self.task_index = 1

    def __run(self):
        while self.is_running:
            try:
                task_class = self.queue.get_nowait()[1]
                self.timer.cancel()
                task_class.run()
            except queue.Empty:
                if not self.timer.is_alive():
                    sec = random.randint(50, 90)
                    logger.info(f'下一个闲时任务将在 {sec} 秒后启动')
                    self.timer = threading.Timer(sec, self.__create_a_leisure_task, ())
                    self.timer.start()
                time.sleep(0.5)
    
    def __create_a_leisure_task(self):
        logger.info('发布了一个闲时任务...')
        self.put(10, self.leisure_task)

    def put(self, priority:int, event):
        priority += self.task_index
        self.task_index += 1
        self.queue.put((priority,event))

    def start(self) -> bool:
        if self.is_running:
            logger.info('事件队列已在运行中')
            return False
        if not self.first_run:
            self.__init__(False)
        if not self.threading.is_alive():
            self.is_running = True
            self.timer.start()
            self.threading.start()
            logger.info('事件队列已启动')
        return self.is_running
        
    def stop(self):
        self.is_running = False
        self.is_first_run = False
        self.timer.cancel()
        self.threading.join()
        logger.info('事件队列已停止')

# 任务处理基类
class BasicTask:
    '''基本任务'''
    def __init__(self, llm:LLMModule, tts:EdgeTTS, captions:Captions, database:Database) -> None:
        self.llm = llm
        self.tts = tts
        self.captions = captions
        self.database = database

    def run():
        '''基本任务运行入口'''
        pass

class DanmuTask(BasicTask):
    def __init__(self, llm:LLMModule, tts:EdgeTTS, captions:Captions, database:Database, data:dict) -> None:
        super(DanmuTask, self).__init__(llm,tts,captions,database)
        self.data = data
    
    def run(self):
        database_history = self.database.get_history()
        logger.info(f'[{self.data["username"]}]：{self.data["message"]}')
        history = generate_history(self.data['message'], database_history, self.data['userid'])
        logger.info(f'[{self.data["username"]}] 获取到的历史记录: {history}')
        respond = self.llm.model.ask(self.data['message'], history=history)
        logger.info(f'[{self.data["username"]}] {self.data["message"]} -> {respond}')
        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not self.tts.speak(respond):
            return
        self.captions.post(self.data['message'], self.data['username'], self.data['userface'], respond)
        play_audio()
        self.database.add_item(self.data['username'], self.data['userid'], self.data['message'], respond)
        logger.info(f'[{self.data["username"]}] 事件处理结束')

class LeisureTask(BasicTask):
    def __init__(self, llm:LLMModule, tts:EdgeTTS, captions:Captions, database:Database) -> None:
        super(LeisureTask, self).__init__(llm,tts,captions,database)
    
    def run(self):
        # history = self.database.get_history()
        active_prompts = ['<生成推文: 胡思乱想>', '<生成推文: AI生活>', '<生成推文: AI思考>', '<生成推文: 表达爱意>', '<生成推文: 情感建议>']
        LeisurePrompt = random.choice(active_prompts)
        respond = self.llm.model.ask(LeisurePrompt, history=[])
        self.database.add_item('闲时任务', '0', LeisurePrompt, respond)
        self.tts.speak(respond)
        self.captions.post('', '', '', respond, leisure=True)
        play_audio()


# WebUI事件处理
class WebUIEventHandler:
    def __init__(self, config: Config, llm:LLMModule, captions:Captions, eventqueue:EventQueue, webui = None, danmu = None, test = None) -> None:
        self.config = config
        self.webui = webui
        self.danmu = danmu
        self.llm = llm
        self.captions = captions
        self.queue = eventqueue
        self.test = test
        self.model:BasicModel = None
        self.chat_history = []

    async def start_all(self):
        self.connect_to_LLM()
        self.connect_to_captions()
        await self.connect_to_blivedm()
        self.start_service()
    
    def start_service(self):
        if self.webui.status.all:
            self.webui.ui.notify('无法启动：已启动了一个进程',type='negative')
            return False
        if self.webui.status.llm and self.webui.status.blivedm and self.webui.status.captions:
            if self.queue.start():
                self.webui.change_all_status(1)
        else:
            self.webui.ui.notify('无法启动：必要的组件未全部连接',type='negative')

    def stop_service(self):
        if not self.webui.status.all:
            self.webui.ui.notify('无法关闭：进程未在运行中',type='negative')
            return False
        self.queue.stop()
        self.webui.change_all_status(0)

    def connect_to_LLM(self):
        if self.webui.status.llm:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        model = self.llm.LoadLLMModule(self.config.LLM_MODEL_LOADER, self.config.LLM_MODEL_PATH, self.config.LLM_ADAPTER_PATH, self.config.LLM_SYSTEM_PROMPT, self.config.LLM_AUTO_SYSTEM_PROMPT, self.config.LLM_EXTRA_ARGS)
        if model:
            self.model = model
            self.llm.model.is_running = True
            self.webui.change_LLM_status(1)
        else:
            self.webui.ui.notify('无法连接至LLM',type='negative')

    async def connect_to_blivedm(self):
        if self.webui.status.blivedm:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        self.danmu.start_client()

    async def disconnect_to_blivedm(self):
        if not self.webui.status.blivedm:
            self.webui.ui.notify('尚未连接！',type='negative')
            return False
        self.danmu.close_client()

    def connect_to_captions(self):
        if self.webui.status.captions:
            self.webui.ui.notify('不能重复连接！',type='negative')
            return False
        if self.captions.connect():
            self.webui.change_captions_status(1)
        else:
            self.webui.ui.notify('无法连接至字幕组件',type='negative')

    def chat_with_LLM(self,prompt):
        if self.webui.LLM_status:
            respond = self.model.ask(prompt,self.chat_history)
            self.chat_history.append([prompt,respond])
            return respond
        else:
            self.webui.ui.notify('LLM未连接',type='warning')

    def CreateATestDanmuEvent(self):
        self.test.CreateADanmuEvent()


# 事件处理分发
class EventHandler:
    def __init__(self, llm:LLMModule, tts:EdgeTTS, captions:Captions, database:Database, eventquene:EventQueue, ui:WebUI = None) -> None:
        self.llm = llm
        self.tts = tts
        self.captions = captions
        self.database = database
        self.quene = eventquene
        self.ui = ui

    def DanmuEvent(self, danmu:DanmakuMessage):
        self.ui.ui_danmu.push(f'{danmu.uname}：{danmu.msg}')
        # self.ui.ui_danmu.push(f'醒目留言 ¥{message.rmb} {message.uname}：{message.message}')
        message = danmu.msg
        username = danmu.uname
        userface = danmu.uface
        userid = danmu.open_id
        if not self.llm.model.is_running or not self.captions.is_connecting or not message_precheck(message):
            return
        userface = get_avatar_base64(userface + '@250x250')
        data = {'message': message, 'username': username, 'userface': f'data:image/png;base64,' + userface, 'userid': userid}
        task = DanmuTask(self.llm, self.tts, self.captions, self.database, data)
        self.quene.put(1, task)
