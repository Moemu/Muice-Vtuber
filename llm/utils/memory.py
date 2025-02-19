def generate_history(prompt: str, data_cursor, user_id: str, user_only: bool = False) -> list[str, str]:
    '''
    生成对话历史
    优先级：用户对话历史(5) > 全局对话历史(5) > 空闲任务历史(1)
    '''
    history = []
    user_history = [item for item in data_cursor if item[3] == user_id]
    
    if not user_only:
        for item in data_cursor[-5:]:
            history.append([item[0], item[4], item[5]])
    for item in user_history[-5:]:
        history.append([item[0], item[4], item[5]])

    # 列表去重并根据时间戳排序
    history = [list(t) for t in set(tuple(i) for i in history)]
    history.sort(key=lambda x: x[0])
    # 移除时间戳
    history = [[item[1], item[2]] for item in history]

    return history