"""
消息过滤器
"""
import re
import logging

logger = logging.getLogger("Muice.filter")

_stop_words:list[str] = []
_STOP_WORDS_DIR = "utils/stop_words/"
_STOP_WORDS_FILES = ["色情词库.txt", "反动词库.txt"]

for file in _STOP_WORDS_FILES:
    with open(_STOP_WORDS_DIR + file, encoding="utf-8") as f:
        for word in f.readlines():
            word.strip()
            _stop_words.append(word)

pattern = '|'.join([re.escape(word.strip()) for word in _stop_words if word.strip()])

def message_filiter(message:str) -> bool:
    """
    消息安全过滤器
    """
    # 如果没有有效的停用词，直接返回安全
    if not pattern:
        return True
    
    # # 使用正则表达式搜索，如果找到匹配项则返回False（不安全）
    # if re.search(pattern, message):
    #     logger.warning(f"{message} 检测到停用词")
    #     return False
    
    return True

# def response_filiter(response:str) -> str:
#     """
#     模型安全过滤器
#     """
#     if not pattern: return response
#     sentenses = response.split("。")
#     for index, sen in enumerate(sentenses):
#         if re.search(pattern, sen):
#             logger.warning(f"{sen} 检测到停用词")
#             sentenses[index] = "(已过滤)我们还是换一个话题聊吧qwq"
#     return "。".join(sentenses)