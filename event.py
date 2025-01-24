from blivedm.blivedm.models.open_live import DanmakuMessage,GiftMessage,SuperChatMessage,GuardBuyMessage
from custom_types import BasicTask,BasicModel
from ui import WebUI
from llm.utils.memory import generate_history
from tts import EdgeTTS
from utils.utils import play_audio,Captions, get_avatar_base64, message_precheck
from config import Config
from sqlite import Database
import queue,threading,time,random,sys

import logging
logger = logging.getLogger('Muice.Event')

# 任务队列
class EventQueue:
    def __init__(self, first_run = True) -> None:
        self.queue = queue.PriorityQueue(maxsize=5)
        self.threading = threading.Thread(target=self.__run, daemon=True)
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


class DanmuTask(BasicTask):
    '''弹幕任务'''
    def run(self):
        database_history = self.database.get_history()
        logger.info(f'[{self.data["username"]}]：{self.data["message"]}')
        history = generate_history(self.data['message'], database_history, self.data['userid'])
        logger.info(f'[{self.data["username"]}] 获取到的历史记录: {history}')
        respond = self.model.ask(self.data['message'], history=history)
        logger.info(f'[{self.data["username"]}] {self.data["message"]} -> {respond}')
        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not self.tts.speak(respond):
            return
        self.captions.post(self.data['message'], self.data['username'], self.data['userface'], respond)
        play_audio()
        self.database.add_item(self.data['username'], self.data['userid'], self.data['message'], respond)
        logger.info(f'[{self.data["username"]}] 事件处理结束')

class GiftTask(BasicTask):
    '''礼物任务'''
    def run(self):
        logger.info(f'[{self.data["username"]}] 赠送了 {self.data["gift_name"]} x {self.data["gift_num"]} 总价值: {self.data["total_value"]}')
        respond = f"感谢 {self.data['username']} 赠送的 {self.data['gift_name']} 喵，雪雪最喜欢你了喵！"
        logger.info(f'[{self.data["username"]}] {self.data["gift_name"]} -> {respond}')
        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not self.tts.speak(respond):
            return
        play_audio()
        self.database.add_gift(self.data['username'], self.data['userid'], self.data['gift_name'], self.data['total_value'])
        logger.info(f'[{self.data["username"]}] 事件处理结束')

class SuperChatTask(BasicTask):
    '''醒目留言任务'''
    def run(self):
        logger.info(f'[{self.data["username"]}] 赠送了 ¥{self.data["rmb"]} 醒目留言：{self.data["message"]}')
        database_history = self.database.get_history()
        history = generate_history(self.data['message'], database_history, self.data['userid'])
        model_output = self.model.ask(self.data['message'], history=history)
        respond = f"感谢 {self.data['username']} 的SuperChat。\n" + model_output
        logger.info(f'[{self.data["username"]}] 醒目留言 -> {respond}')
        logger.info(f'[{self.data["username"]}] TTS处理...')
        if not self.tts.speak(respond):
            return
        play_audio()
        self.database.add_item(self.data['username'], self.data['userid'], f'(¥{self.data["rmb"]}醒目留言)' + self.data['message'], model_output)
        logger.info(f'[{self.data["username"]}] 事件处理结束')

class BuyGuardTask(BasicTask):
    '''上舰任务'''
    def run(self):
        logger.info(f'{self.data["username"]} 购买了大航海等级 {self.data["guard_level"]}')
        respond = f'感谢 {self.data["username"]} 的舰长喵！会有什么神奇的事情发生呢？'
        logger.info(f'{self.data["username"]} TTS处理...')
        if not self.tts.speak(respond):
            return
        play_audio()
        self.database.add_gift(self.data['username'], self.data['userid'], f'大航海等级{self.data["guard_level"]}', self.data['price'])
        logger.info(f'{self.data["username"]} 事件处理结束')

class LeisureTask(BasicTask):
    def run(self):
        # history = self.database.get_history()
        active_prompts = ['<生成推文: 胡思乱想>', '<生成推文: AI生活>', '<生成推文: AI思考>', '<生成推文: 表达爱意>', '<生成推文: 情感建议>']
        LeisurePrompt = random.choice(active_prompts)
        respond = self.model.ask(LeisurePrompt, history=[])
        self.database.add_item('闲时任务', '0', LeisurePrompt, respond)
        self.tts.speak(respond)
        self.captions.post('', '', '', respond, leisure=True)
        play_audio()


# WebUI事件处理(总事件处理)
class WebUIEventHandler:
    def __init__(self, config: Config, model: BasicModel, captions:Captions, eventqueue:EventQueue, webui = None, danmu = None, test = None) -> None:
        self.config = config
        self.model = model
        self.webui = webui
        self.danmu = danmu
        self.captions = captions
        self.queue = eventqueue
        self.test = test
        self.model = model
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
        try:
            logger.info(f"加载模型：{self.config.LLM_MODEL_LOADER}")
            self.model.load(self.config.LLM_MODEL_PATH, self.config.LLM_ADAPTER_PATH, self.config.LLM_SYSTEM_PROMPT, self.config.LLM_AUTO_SYSTEM_PROMPT, self.config.LLM_EXTRA_ARGS)
            self.webui.change_LLM_status(1) if self.model.is_running else self.webui.change_LLM_status(0)
        except:
            self.webui.ui.notify('无法连接至LLM',type='negative')
            logger.error(f"无法加载模型：{self.config.LLM_MODEL_LOADER}", exc_info=True)

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

    def shutdown(self, signum, frame):
        self.model.is_running = False
        self.queue.stop()
        self.danmu.close_client()
        self.captions.disconnect()
        self.webui.app.shutdown()
        sys.exit(0)

# 事件处理分发
class EventHandler:
    def __init__(self, model:BasicModel, tts:EdgeTTS, captions:Captions, database:Database, eventquene:EventQueue, ui:WebUI = None) -> None:
        self.model = model
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
        if not self.model.is_running or not self.captions.is_connecting or not message_precheck(message):
            return
        userface = get_avatar_base64(userface + '@250x250')
        data = {'message': message, 'username': username, 'userface': f'data:image/png;base64,' + userface, 'userid': userid}
        task = DanmuTask(self.model, self.tts, self.captions, self.database, data)
        self.quene.put(5, task)

    def GiftEvent(self, gift:GiftMessage):
        if not gift.paid:
            return
        username = gift.uname
        userid = gift.open_id
        gift_name = gift.gift_name
        total_value = gift.price * gift.gift_num / 1000
        data = {'username': username, 'userid': userid, 'gift_name': gift_name, 'gift_num': gift.gift_num, 'total_value': total_value}
        task = GiftTask(self.llm, self.tts, self.captions, self.database, data)
        self.quene.put(3, task)

    def SuperChatEvent(self, superchat:SuperChatMessage):
        username = superchat.uname
        userid = superchat.open_id
        message = superchat.message
        rmb = superchat.rmb
        data = {'username': username, 'userid': userid, 'message': message, 'rmb': rmb}
        task = SuperChatTask(self.llm, self.tts, self.captions, self.database, data)
        self.quene.put(1, task)

    def GuardBuyEvent(self, message:GuardBuyMessage):
        username = message.user_info.uname
        userid = message.user_info.open_id
        guard_level = message.guard_level
        price = message.price / 1000
        data = {'username': username, 'userid': userid, 'guard_level': guard_level, 'price': price}
        task = BuyGuardTask(self.llm, self.tts, self.captions, self.database, data)
        self.quene.put(1, task)