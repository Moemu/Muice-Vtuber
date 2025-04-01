from llm import Message
from sqlite import Database

async def generate_history(database:Database, prompt: str, user_id: str, user_only: bool = False) -> list[Message]:
    '''
    生成对话历史
    优先级：用户对话历史(5) > 全局对话历史(5)
    '''
    history = await database.get_history(user_id, limit = 5)
    global_history = await database.get_history(limit = 10)
    
    if not user_only:
        history += global_history

    return list(set(history))