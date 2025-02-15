import sys,yaml

class Config:
    def __init__(self) -> None:
        with open('configs.yml','r',encoding='utf-8') as f:
            self.config = yaml.load(f, Loader=yaml.FullLoader)
        self.__load_config_file()
        self.PYTHON_ENV = sys.executable

    def __load_config_file(self) -> None:
        self.DANMU_ACCESS_KEY_ID = self.config['danmu']['access_key_id']
        self.DANMU_ACCESS_KEY_SECRET = self.config['danmu']['access_key_secret']
        self.DANMU_APP_ID = self.config['danmu']['app_id']
        self.DANMU_ROOM_OWNER_AUTH_CODE = self.config['danmu']['room_owner_auth_code']
        self.LLM_MODEL_CONFIG = self.config['model']
        self.LLM_MODEL_LOADER = self.config['model']['loader']
        self.BOT_APPID = self.config['bot']['appid']
        self.BOT_TOKEN = self.config['bot']['token']
        self.BOT_SECRET = self.config['bot']['secret']

    def save(self, key:str, value:str) -> None:
        self.config[key] = value
        self.__load_config_file()
        with open('configs.yml','w',encoding='utf-8') as f:
            yaml.dump(self.config, f)