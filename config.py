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
        self.LLM_MODEL_LOADER = self.config['model']['loader']
        self.LLM_MODEL_PATH = self.config['model']['model_path']
        self.LLM_ADAPTER_PATH = self.config['model']['adapter_path']
        self.LLM_EXTRA_ARGS = self.config['model']['extra_args']
        self.LLM_SYSTEM_PROMPT = self.config['model']['system_prompt']
        self.LLM_AUTO_SYSTEM_PROMPT = self.config['model']['auto_system_prompt']
        self.BOT_APPID = self.config['bot']['appid']
        self.BOT_TOKEN = self.config['bot']['token']
        self.BOT_SECRET = self.config['bot']['secret']

    def save(self, key:str, value:str) -> None:
        self.config[key] = value
        self.__load_config_file()
        with open('configs.yml','w',encoding='utf-8') as f:
            yaml.dump(self.config, f)