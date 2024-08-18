import importlib

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

    def LoadLLMModule(self, LLM_MODEL_LOADER:str, LLM_MODEL_PATH:str, LLM_ADAPTER_PATH:str) -> BasicModel|bool:
        try:
            model = importlib.import_module(f"llm.{LLM_MODEL_LOADER}")
            model = model.llm(LLM_MODEL_PATH, LLM_ADAPTER_PATH)
            self.model = model
            return model
        except:
            return False