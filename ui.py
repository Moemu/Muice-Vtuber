from nicegui import ui,app
from config import Config
import logging

ui.dark_mode().enable()
config = Config()
logger = logging.getLogger(__name__)

class WebUI:

    class label:
        all:ui.label = None
        llm:ui.label = None
        blivedm:ui.label = None
        captions:ui.label = None
        bot:ui.label = None
        realtime_chat:ui.label = None

    class icon:
        all:ui.label = None
        llm:ui.icon = None
        blivedm:ui.icon = None
        captions:ui.label = None
        bot:ui.label = None
        realtime_chat:ui.label = None

    class status:
        all:int = 0
        llm:int = 0
        blivedm:int = 0
        captions:int = 0
        bot:int = 0
        realtime_chat:int = 0

    def __init__(self,WebUIEventHandler = None) -> None:
        self.ui_danmu = None
        self.action = WebUIEventHandler
        self.app = app
        self.ui = ui

    def __Load(self):
        with ui.tabs().classes('w-full') as tabs:
            tab_start = ui.tab("开始")
            tab_danmu = ui.tab("弹幕")
            tab_control = ui.tab("控制台")
            # tab_setting = ui.tab("设置")

        with ui.tab_panels(tabs, value=tab_start).classes('w-full'):
            with ui.tab_panel(tab_start):
                with ui.row():
                    with ui.card().classes('w-50'):
                        ui.label('运行状态').style('font-size: large')
                        with ui.row().style('line-height: 1'):
                            ui.label('消息处理')
                            self.icon.all = ui.icon('circle',color='red')
                            self.label.all = ui.label('未运行')
                        with ui.row().style('line-height: 1'):
                            ui.label('LLM状态')
                            self.icon.llm = ui.icon('circle',color='red')
                            self.label.llm = ui.label('未连接')
                        with ui.row().style('line-height: 1'):
                            ui.label('Blivedm状态')
                            self.icon.blivedm = ui.icon('circle',color='red')
                            self.label.blivedm = ui.label('未连接')
                        with ui.row().style('line-height: 1'):
                            ui.label('字幕组件状态')
                            self.icon.captions = ui.icon('circle',color='red')
                            self.label.captions = ui.label('未连接')
                        with ui.row().style('line-height: 1'):
                            ui.label('QQBot状态')
                            self.icon.bot = ui.icon('circle',color='red')
                            self.label.bot = ui.label('未连接')
                        with ui.row().style('line-height: 1'):
                            ui.label('实时聊天状态')
                            self.icon.realtime_chat = ui.icon('circle',color='red')
                            self.label.realtime_chat = ui.label('未启动')

                with ui.card().classes('w-50'):
                    ui.label('总操作台').style('font-size: large')
                    ui.button('一键启动',on_click=self.action.start_all)
                    ui.button('开始消息处理',on_click=self.action.start_service)
                    ui.button('终止消息处理',on_click=self.action.stop_service)    

                with ui.card().classes('w-50'):
                    ui.label('LLM操作台').style('font-size: large')
                    ui.button('连接到LLM',on_click=self.action.connect_to_LLM)
                    
                with ui.card().classes('w-50'):
                    ui.label('弹幕控制台').style('font-size: large')
                    ui.button('连接到blivedm',on_click=self.action.connect_to_blivedm)
                    ui.button('取消连接',on_click=self.action.disconnect_to_blivedm)
                    ui.button('创建一个测试弹幕事件',on_click=self.action.CreateATestDanmuEvent)

                with ui.card().classes('w-50'):
                    ui.label('字幕组件控制台').style('font-size: large')
                    ui.button('连接到字幕组件',on_click=self.action.connect_to_captions)

                with ui.card().classes('w-50'):
                    ui.label('实时对话控制').style('font-size: large')
                    ui.button('启动实时对话',on_click=self.action.start_realtime_chat)
                    ui.button('终止实时对话',on_click=self.action.stop_realtime_chat)                      
            
            with ui.tab_panel(tab_danmu):
                self.ui_danmu =ui.log().classes("w-full overflow-auto").style("height: 50rem")

            with ui.tab_panel(tab_control):
                ui_log = ui.log().classes("w-full overflow-auto",replace='').style("height: 50rem")

            # with ui.tab_panel(tab_setting):
            #     with ui.row():
            #         with ui.card().classes('w-50'):
            #             ui.label("B站弹幕监听")
            #             ui.input(label='ACCESS_KEY_ID', value=config.DANMU_ACCESS_KEY_ID, on_change=lambda e: config.save("DANMU_ACCESS_KEY_ID", e.value)).classes('w-64')
            #             ui.input(label='ACCESS_KEY_SECRET', value=config.DANMU_ACCESS_KEY_SECRET, on_change=lambda e: config.save("DANMU_ACCESS_KEY_SECRET", e.value)).classes('w-64')
            #             ui.input(label='APP_ID', value=config.DANMU_APP_ID, on_change=lambda e: config.save("DANMU_APP_ID", e.value)).classes('w-64')
            #             ui.input(label='ROOM_OWNER_AUTH_CODE', value=config.DANMU_ROOM_OWNER_AUTH_CODE, on_change=lambda e: config.save("DANMU_ROOM_OWNER_AUTH_CODE", e.value)).classes('w-64')
            #         with ui.card():
            #             ui.label("LLM类")
            #             ui.select(label="MODEL_LOADER", options=["api","llmtuner","transformers","spark"], with_input=True, value=config.LLM_MODEL_LOADER, on_change=lambda e: config.save("LLM_MODEL_LOADER", e.value)).classes('w-64')
            #             ui.input(label='MODEL_PATH', value=config.LLM_MODEL_PATH, on_change=lambda e: config.save("LLM_MODEL_PATH", e.value)).classes('w-64')
            #             ui.input(label='ADAPTER_PATH', value=config.LLM_ADAPTER_PATH, on_change=lambda e: config.save("LLM_ADAPTER_PATH", e.value)).classes('w-64')
        
        ui.run(title="Muice Vtuber", favicon='src/favicon.png', reload=False, show=False, language='zh-CN', port=8081, show_welcome_message = False)

    def start(self):
        return self.__Load()

    def change_all_status(self, status):
        if status:
            self.icon.all.classes('text-green')
            self.label.all.set_text('正在运行')
            self.status.all = 1
        else:
            self.icon.all.classes(remove = 'text-green', replace = 'text-red')
            self.label.all.set_text('未运行')
            self.status.all = 0

    def change_LLM_status(self, status):
        if status:
            self.icon.llm.classes('text-green')
            self.label.llm.set_text('已连接')
            self.status.llm = 1
        else:
            self.icon.llm.classes(remove = 'text-green', replace = 'text-red')
            self.label.llm.set_text('未连接')
            self.status.llm = 0

    def change_blivedm_status(self, status):
        if status:
            self.icon.blivedm.classes('text-green')
            self.label.blivedm.set_text('已连接')
            self.status.blivedm = 1
        else:
            self.icon.blivedm.classes(remove = 'text-green', replace = 'text-red')
            self.label.blivedm.set_text('未连接')
            self.status.blivedm = 0

    def change_captions_status(self, status):
        if status:
            self.icon.captions.classes('text-green')
            self.label.captions.set_text('已连接')
            self.status.captions = 1
        else:
            self.icon.captions.classes(remove = 'text-green', replace = 'text-red')
            self.label.captions.set_text('未连接')
            self.status.captions = 0

    def change_bot_status(self, status):
        if status:
            self.icon.bot.classes('text-green')
            self.label.bot.set_text('已连接')
            self.status.bot = 1
        else:
            self.icon.bot.classes(remove = 'text-green', replace = 'text-red')
            self.label.bot.set_text('未连接')
            self.status.bot = 0

    def change_realtime_chat_status(self, status):
        if status:
            self.icon.realtime_chat.classes('text-green')
            self.label.realtime_chat.set_text('已启动')
            self.status.realtime_chat = 1
        else:
            self.icon.realtime_chat.classes(remove = 'text-green', replace = 'text-red')
            self.label.realtime_chat.set_text('未启动')
            self.status.realtime_chat = 0