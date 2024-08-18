from nicegui import ui,app
from config import Config
import importlib,threading,asyncio,logging
from danmu import Danmu

ui.dark_mode().enable()
config = Config()
logger = logging.getLogger(__name__)

class MyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(MyThread, self).__init__(*args, **kwargs)
        self._exception = None

    def run(self):
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)
        except Exception as e:
            self._exception = e

    def join(self, *args, **kwargs):
        super(MyThread, self).join(*args, **kwargs)
        if self._exception:
            raise self._exception

class Status:
    def __init__(self) -> None:
        self.LLM_status = 0
        self.blivedm_status = 0

    def change_LLM_status(self, status):
        if status:
            self.iconLLM.classes('text-green')
            self.llm.set_text('已连接')
            self.LLM_status = 1
        else:
            self.iconLLM.classes('text-red')
            self.llm.set_text('未连接')
            self.LLM_status = 0

    def change_blivedm_status(self, status):
        if status:
            self.iconblivedm.classes('text-green')
            self.blivedm.set_text('已连接')
            self.blivedm_status = 1
        else:
            self.iconblivedm.classes(remove = 'text-green', replace = 'text-red')
            self.blivedm.set_text('未连接')
            self.blivedm_status = 0


class Action:
    def __init__(self) -> None:
        self.chat_history = []

    def connect_to_LLM(self):
        if status.LLM_status:
            ui.notify('不能重复连接！',type='negative')
            return False
        model = importlib.import_module(f"llm.{config.LLM_MODEL_LOADER}")
        try:
            self.model = model.llm(config.LLM_MODEL_PATH, config.LLM_ADAPTER_PATH)
            status.change_LLM_status(1)
        except:
            ui.notify('无法连接至LLM',type='negative')

    async def connect_to_blivedm(self):
        if status.blivedm_status:
            ui.notify('不能重复连接！',type='negative')
            return False
        danmu.start_client()
        app.on_exception(lambda exception: ui.notify('连接失败',type='negative'))
        # asyncio.create_task(danmu.start_client(config))

    async def disconnect_to_blivedm(self):
        if not status.blivedm_status:
            ui.notify('尚未连接！',type='negative')
            return False
        danmu.close_client()

    def chat_with_LLM(self,prompt):
        if status.LLM_status:
            respond = self.model.chat(prompt,self.chat_history)
            self.chat_history.append([prompt,respond])
            return respond
        else:
            ui.notify('LLM未连接',type='warning')

status = Status()
action = Action()

with ui.tabs().classes('w-full') as tabs:
    tab_start = ui.tab("开始")
    tab_danmu = ui.tab("弹幕")
    tab_control = ui.tab("控制台")
    tab_setting = ui.tab("设置")

with ui.tab_panels(tabs, value=tab_start).classes('w-full'):
    with ui.tab_panel(tab_start):
        with ui.row():
            with ui.card().classes('w-50'):
                ui.label('运行状态').style('font-size: large')
                with ui.row().style('line-height: 1'):
                    ui.label('LLM状态')
                    status.iconLLM = ui.icon('circle',color='red')
                    status.llm = ui.label('未连接')
                with ui.row().style('line-height: 1'):
                    ui.label('Blivedm状态')
                    status.iconblivedm = ui.icon('circle',color='red')
                    status.blivedm = ui.label('未连接')

        with ui.card().classes('w-50'):
            ui.label('LLM操作台').style('font-size: large')
            ui.button('连接到LLM',on_click=action.connect_to_LLM)
            
        with ui.card().classes('w-50'):
            ui.label('弹幕控制台').style('font-size: large')
            ui.button('连接到blivedm',on_click=action.connect_to_blivedm)
            ui.button('取消连接',on_click=action.disconnect_to_blivedm)
                
    
    with ui.tab_panel(tab_danmu):
        ui_danmu =ui.log().classes("w-full overflow-auto").style("height: 50rem")

    with ui.tab_panel(tab_control):
        ui_log = ui.log().classes("w-full overflow-auto",replace='').style("height: 50rem")

    with ui.tab_panel(tab_setting):
        with ui.row():
            with ui.card().classes('w-50'):
                ui.label("B站弹幕监听")
                ui.input(label='ACCESS_KEY_ID', value=config.DANMU_ACCESS_KEY_ID, on_change=lambda e: config.save("DANMU_ACCESS_KEY_ID", e.value)).classes('w-64')
                ui.input(label='ACCESS_KEY_SECRET', value=config.DANMU_ACCESS_KEY_SECRET, on_change=lambda e: config.save("DANMU_ACCESS_KEY_SECRET", e.value)).classes('w-64')
                ui.input(label='APP_ID', value=config.DANMU_APP_ID, on_change=lambda e: config.save("DANMU_APP_ID", e.value)).classes('w-64')
                ui.input(label='ROOM_OWNER_AUTH_CODE', value=config.DANMU_ROOM_OWNER_AUTH_CODE, on_change=lambda e: config.save("DANMU_ROOM_OWNER_AUTH_CODE", e.value)).classes('w-64')
            with ui.card():
                ui.label("LLM类")
                ui.select(label="MODEL_LOADER", options=["api","llmtuner","transformers"], with_input=True, value=config.LLM_MODEL_LOADER, on_change=lambda e: config.save("LLM_MODEL_LOADER", e.value)).classes('w-64')
                ui.input(label='MODEL_PATH', value=config.LLM_MODEL_PATH, on_change=lambda e: config.save("LLM_MODEL_PATH", e.value)).classes('w-64')
                ui.input(label='ADAPTER_PATH', value=config.LLM_ADAPTER_PATH, on_change=lambda e: config.save("LLM_ADAPTER_PATH", e.value)).classes('w-64')

danmu = Danmu(config,ui_danmu,status)

class UI:
    def __init__(self) -> None:
        # self.log = log
        # self.danmu = danmu
        pass

    def start(self):
        ui.run(title="Muice Vtuber", favicon='src/favicon.png', reload=True, show=False, language='zh-CN')