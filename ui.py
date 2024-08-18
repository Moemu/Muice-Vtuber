from nicegui import ui
from config import Config
import logging

ui.dark_mode().enable()
config = Config()
logger = logging.getLogger(__name__)

class WebUI:
    def __init__(self,WebUIEventHandler = None) -> None:
        self.LLM_status = 0
        self.blivedm_status = 0
        self.ui_danmu = None
        self.action = WebUIEventHandler
        self.ui = ui

    def __Load(self):
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
                            self.iconLLM = ui.icon('circle',color='red')
                            self.llm = ui.label('未连接')
                        with ui.row().style('line-height: 1'):
                            ui.label('Blivedm状态')
                            self.iconblivedm = ui.icon('circle',color='red')
                            self.blivedm = ui.label('未连接')

                with ui.card().classes('w-50'):
                    ui.label('LLM操作台').style('font-size: large')
                    ui.button('连接到LLM',on_click=self.action.connect_to_LLM)
                    
                with ui.card().classes('w-50'):
                    ui.label('弹幕控制台').style('font-size: large')
                    ui.button('连接到blivedm',on_click=self.action.connect_to_blivedm)
                    ui.button('取消连接',on_click=self.action.disconnect_to_blivedm)
                        
            
            with ui.tab_panel(tab_danmu):
                self.ui_danmu =ui.log().classes("w-full overflow-auto").style("height: 50rem")

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
        
        ui.run(title="Muice Vtuber", favicon='src/favicon.png', reload=False, show=False, language='zh-CN')

    def start(self):
        return self.__Load()

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