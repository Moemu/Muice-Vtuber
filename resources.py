from ._types import BasicTTS
from config import Config
from llm import BasicModel
from utils.utils import Captions
from .sqlite import Database
from config import get_model_config
from typing import Type, Optional

import importlib

def _load_model(model_config_types:str = "default") -> BasicModel:
    """
    初始化模型类
    """
    model_config = get_model_config(model_config_types = model_config_types)
    module_name = f"llm.{model_config.loader}"
    module = importlib.import_module(module_name)
    ModelClass: Optional[Type[BasicModel]] = getattr(module, model_config.loader, None)

    if not ModelClass:
        raise ValueError(f"Model {model_config.loader} Not Found!")
    
    model = ModelClass(model_config)
    model.load()
    return model

class Resources:
    """外部模块资源"""
    _instance: Optional["Resources"] = None
    
    def __init__(self, config:Config, model:BasicModel, leisure_model:BasicModel, multimodal:BasicModel, tts:BasicTTS, captions:Captions, database:Database) -> None:
        self.config = config
        self.model = model
        self.leisure_model = leisure_model
        self.multimodal = multimodal
        self.tts = tts
        self.captions = captions
        self.database = database

    @classmethod
    def init(cls):
        if cls._instance is None:
            config = Config()
            tts_module = importlib.import_module("tts")
            tts = getattr(tts_module, config.TTS_LOADER)(config.TTS_CONFIG)

            model = _load_model()
            leisure_model = _load_model("leisure")
            multimodal = _load_model("multimodal")
            captions = Captions()
            database = Database()

            cls._instance = cls(config, model, leisure_model, multimodal, tts, captions, database)
    
    @classmethod
    def get(cls) -> "Resources":
        if cls._instance is None:
            raise RuntimeError("Resources not initialized. Call Resources.init() first.")
        return cls._instance