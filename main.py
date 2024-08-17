from ui import UI
import logging

logging.basicConfig(format='[%(levelname)s] %(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)
ui = UI()

if __name__ in {"__main__", "__mp_main__"}:
    # asyncio.run(start_danmu())
    # model = importlib.import_module(f"llm.{config.LLM_MODEL_LOADER}")
    # model = model.llm(config.LLM_MODEL_PATH, config.LLM_ADAPTER_PATH)
    ui.start()