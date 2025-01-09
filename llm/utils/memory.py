def generate_history(prompt: str, data_cursor, user_id: str) -> list:
    '''
    生成对话历史
    优先级：用户对话历史(5) > 全局对话历史(5) > 空闲任务历史(1)
    '''
    history = []
    user_history = [item for item in data_cursor if item[3] == user_id]
    
    for item in data_cursor[-5:]:
        history.append([item[4],item[5]])
    for item in user_history[-5:]:
        history.append([item[4],item[5]])

    # 列表去重
    history = [list(t) for t in set(tuple(i) for i in history)]

    return history