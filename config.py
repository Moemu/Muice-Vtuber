import sys
import yaml
import os
from typing import Optional
from services.llm import ModelConfig
from pathlib import Path

MODELS_CONFIG_PATH = Path("configs/models.yml").resolve()

class Config:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

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
        self.TTS_LOADER = self.config['tts']['loader']
        self.TTS_CONFIG = self.config['tts']
        self.WEATHER = self.config['weather']

    def save(self, key:str, value:str) -> None:
        self.config[key] = value
        self.__load_config_file()
        with open('configs.yml','w',encoding='utf-8') as f:
            yaml.dump(self.config, f)

def get_model_config(model_config_types: Optional[str] = "default") -> ModelConfig:
    """
    从配置文件 `configs/models.yml` 中获取指定模型的配置文件

    :model_config_name: (可选)模型配置名称。若为空，则先寻找配置了 `default: true` 的首个配置项，若失败就再寻找首个配置项
    若都不存在，则抛出 `FileNotFoundError`
    """
    if not os.path.isfile(MODELS_CONFIG_PATH):
        raise FileNotFoundError("configs/models.yml 不存在！请先创建")

    with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
        configs = yaml.load(f, Loader=yaml.FullLoader)

    if not configs:
        raise ValueError("configs/models.yml 为空，请先至少定义一个模型配置")

    model_config = next((config for config in configs.values() if config.get(model_config_types)), None)  # 尝试获取默认配置
    if not model_config:
        model_config = next(iter(configs.values()), None)  # 尝试获取第一个配置

    if not model_config:
        raise FileNotFoundError("configs/models.yml 中不存在有效的模型配置项！")

    model_config = ModelConfig(**model_config)

    return model_config