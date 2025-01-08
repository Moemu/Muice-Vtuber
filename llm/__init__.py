import importlib
import logging

logger = logging.getLogger('Muice.LLM')

class BasicModel:
    def __init__(self):
        self.is_running = False

    def ask(self, prompt:str, history:list) -> str:
        """
        模型交互询问
        """
        pass

class LLMModule:
    def __init__(self) -> None:
        self.model:BasicModel = None

    def LoadLLMModule(self, LLM_MODEL_LOADER:str, LLM_MODEL_PATH:str, LLM_ADAPTER_PATH:str, *args, **kwargs) -> BasicModel|bool:
        try:
            logger.info(f"加载模型：{LLM_MODEL_LOADER}")
            model = importlib.import_module(f"llm.{LLM_MODEL_LOADER}")
            model = model.llm(LLM_MODEL_PATH, LLM_ADAPTER_PATH, *args, **kwargs)
            self.model = model
            return model
        except:
            logger.error(f"无法加载模型：{LLM_MODEL_LOADER}", exc_info=True)
            return False