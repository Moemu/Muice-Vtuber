from dataclasses import dataclass

@dataclass
class MessageData:
    """提取后的消息体"""
    username: str = ""
    """用户名"""
    userid: str = ""
    """用户B站ID"""
    userface: str = ""
    """用户头像"""

    message: str = ""
    """弹幕消息"""

    gift_name: str = ""
    """礼物名称"""
    gift_num: int = 0
    """礼物数量"""
    total_value: float = 0
    """总价值（rmb）"""
    guard_level: int = 0
    """大航海等级"""

    fans_medal_level: int = 0
    """粉丝牌等级"""

    def __add__(self, other: "MessageData") -> "MessageData":
        self.message += f"。{other.message}"
        return self
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(userid={self.userid}, message={self.message})"