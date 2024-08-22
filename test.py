from blivedm.blivedm.models import open_live as open_models
from event import EventHandler
import dataclasses

@dataclasses.dataclass
class DemoDanmakuMessage(open_models.DanmakuMessage):
    """
    弹幕消息
    """

    uname: str = 'Moemu'
    """用户昵称"""
    open_id: str = '12345'
    """用户唯一标识"""
    uface: str = 'https://img.snowy.moe/head.png'
    """用户头像"""
    timestamp: int = 0
    """弹幕发送时间秒级时间戳"""
    room_id: int = 0
    """弹幕接收的直播间"""
    msg: str = 'Hello World!'
    """弹幕内容"""
    msg_id: str = '0'
    """消息唯一id"""
    guard_level: int = 0
    """对应房间大航海等级"""
    fans_medal_wearing_status: bool = True
    """该房间粉丝勋章佩戴情况"""
    fans_medal_name: str = ''
    """粉丝勋章名"""
    fans_medal_level: int = 0
    """对应房间勋章信息"""
    emoji_img_url: str = ''
    """表情包图片地址"""
    dm_type: int = 0
    """弹幕类型 0：普通弹幕 1：表情包弹幕"""

class Test:
    def __init__(self, EventHandler:EventHandler) -> None:
        self.EventHandler = EventHandler

    def CreateADanmuEvent(self) -> None:
        self.EventHandler.DanmuEvent(DemoDanmakuMessage)