import sys,json

class Config:
    def __init__(self) -> None:
        with open('config.json','r',encoding='utf-8') as f:
            self.config = json.load(f)
        self.__load_config_file()
        self.PYTHON_ENV = sys.executable

    def __load_config_file(self) -> None:
        self.DANMU_ACCESS_KEY_ID = self.config['DANMU_ACCESS_KEY_ID']
        self.DANMU_ACCESS_KEY_SECRET = self.config['DANMU_ACCESS_KEY_SECRET']
        self.DANMU_APP_ID = self.config['DANMU_APP_ID']
        self.DANMU_ROOM_OWNER_AUTH_CODE = self.config['DANMU_ROOM_OWNER_AUTH_CODE']
        self.LLM_MODEL_LOADER = self.config['LLM_MODEL_LOADER']
        self.LLM_MODEL_PATH = self.config['LLM_MODEL_PATH']
        self.LLM_ADAPTER_PATH = self.config['LLM_ADAPTER_PATH']

    def save(self, key:str, value:str) -> None:
        self.config[key] = value
        self.__load_config_file()
        with open('config.json','w',encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=4)