from services.llm import Message
from infra.database import Database

async def generate_history(database:Database, prompt: str, user_id: str, user_only: bool = False) -> list[Message]:
    '''
    生成对话历史
    组合：用户对话历史(5) + 全局对话历史(10)
    '''
    history = await database.get_history(user_id, limit = 5)
    global_history = await database.get_history(limit = 10)
    
    if not user_only:
        history += global_history

    for index, item in enumerate(history):
        history[index].danmu = f"<{item.username}> {item.danmu}"

    return list(set(history))