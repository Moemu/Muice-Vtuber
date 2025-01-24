import botpy
import random
import time
import fastapi
import uvicorn
import asyncio
import importlib
from botpy.types.message import Message
from botpy.types.message import Reference
from custom_types import BasicModel
from config import Config
from datetime import datetime
from botpy.logging import DEFAULT_FILE_HANDLER

DEFAULT_FILE_HANDLER["filename"] = f'logs/{time.strftime("%Y-%m-%d", time.localtime())}.botpy.log'
DEFAULT_FILE_HANDLER["format"] = '[%(asctime)s] [%(name)s] [%(levelname)s] %(funcName)s: %(message)s'
DEFAULT_FILE_HANDLER["level"] = 10

app = fastapi.FastAPI()

class FortuneTeller:
    def __init__(self):
        self.fortunes = [
            {"name": "大吉", "probability": 0.2},
            {"name": "中吉", "probability": 0.4},
            {"name": "小吉", "probability": 0.3},
            {"name": "不太吉", "probability": 0.1}
        ]

        self.events = [
            {"name":"写代码", "good":"今天Debug报错少", "bad":"今天Debug报错多", "tag":"程序员"},
            {"name":"写网页前端", "good":"今天写出来的网页很漂亮", "bad":"你会发现你的CSS不起作用", "tag":"程序员"},
            {"name":"为你的项目想一个功能", "good":"实现后你的项目会大受欢迎", "bad":"实现的时间会比预期长", "tag":"程序员"},
            {"name":"构想一个小工具", "good":"没准很实用", "bad":"脑子被榨干了~下次再说~", "tag":"程序员"},
            {"name":"编译你的项目", "good":"有些问题编译后才能发现", "bad":"IDE的报错都没解决完就想编译?", "tag":"程序员"},
            {"name":"解决一个bug", "good":"解决起来会非常简单", "bad":"小心屎山", "tag":"程序员"},
            {"name":"暴力测试你的应用", "good":"增加上线安全性", "bad":"先完成基本功能再说", "tag":"程序员"},
            {"name":"换个密码", "good":"定期更换密码有利于确保账户的安全性", "bad":None,"tag":"其他"},
            {"name":"写博客", "good":"今天博文会帮助很多人", "bad":"没人会看你的博文", "tag":"博主"},
            {"name":"写一篇随笔", "good":"未来的你会看的", "bad":"这篇随笔有可能会被遗忘", "tag":"博主"},
            {"name":"逛逛别人的博客", "good":"没准可以找到志同道合的朋友", "bad":"也许今天找到的大多不再更新了", "tag":"博主"},
            {"name":"写作业", "good":"今天效率很高", "bad":"你会很快被其他事情分心", "tag":"学生"},
            {"name":"学习一下", "good":"偶尔努力一下有助于提高成绩", "bad":"今天学的效率会很低", "tag":"学生"},
            {"name":"复习一下", "good":"重要性不用我多说了吧", "bad":"很没意思", "tag":"学生"},
            {"name":"做视频", "good":"今天你会很有创意", "bad":"可能今天没有什么创意", "tag":"UP主"},
            {"name":"去B站刷视频", "good":"今天B友又有了很多活", "bad":"你会遇到很多梗小鬼", "tag":"ACGNer"},
            {"name":"去A站看番", "good":"或许今天会有新番", "bad":"A站还没有买新番", "tag":"ACGNer"},
            {"name":"看一部新番", "good":"这次的新番不错", "bad":"感觉不如...", "tag":"ACGNer"},
            {"name":"回顾一下看过的番", "good":"经典永不过时", "bad":"下次再说", "tag":"ACGNer"},
            {"name":"看漫画", "good":"ACGN一家亲", "bad":"找漫画是件费劲的事情", "tag":"ACGNer"},
            {"name":"看轻小说", "good":"ACGN一家亲", "bad":"找小说是件费劲的事情", "tag":"ACGNer"},
            {"name":"回顾以前玩过的游戏", "good":"都是回忆", "bad":"下次一定", "tag":"ACGNer"},
            {"name":"发个空间/朋友圈", "good":"你会收获很多点赞", "bad":"没有人在意你", "tag":"社交"},
            {"name":"打音游", "good":"今天可以拿下很多图", "bad":"你会收到很多好", "tag":"ACGNer"},
            {"name":"推Gal", "good":"你会推得很爽", "bad":"你会被刀哭", "tag":"ACGNer"},
            {"name":"找Gal玩", "good":"扩展下后宫", "bad":"避免审美疲劳", "tag":"ACGNer"},
            {"name":"抽卡", "good":"今天一定出货", "bad":"喜提保底", "tag":"ACGNer"},
            {"name":"许一个愿望", "good":"没准就实现了呢~", "bad":None,"tag":"其他"},
            {"name":"尝试一个新APP", "good":"你的生活会很有效率", "bad":"广告大于功能", "tag":"其他"},
            {"name":"看看今天的探索队列", "good":"愿望单又多了几位新成员", "bad":"全是三国杀", "tag":"ACGNer"},
            {"name":"听新歌", "good":"推荐给你的都是好东西", "bad":"还不如歌单里面的经典", "tag":"其他"},
            {"name":"试一下新歌单", "good":"没准能发现宝藏歌曲", "bad":"流量歌单没有意思", "tag":"其他"},
            {"name":"唱首歌给朋友", "good":"太好听了吧~简直就是天籁", "bad":"人家不屑于听你的歌", "tag":"社交"},
            {"name":"睡觉", "good":"都抽到我了不去睡一下怎么行?", "bad":"很容易睡过头", "tag":"日常"},
            {"name":"早睡", "good":"补充一下精神", "bad":"你的工作还有很多", "tag":"日常"},
            {"name":"熬夜", "good":"今晚就可以完成所有工作辣", "bad":"白天会把你熬夜的时间补回来", "tag":"日常"},
            {"name":"通宵", "good":"就看个日出应该没什么的吧(心虚)", "bad":"你会肾虚", "tag":"日常"},
            {"name":"逛某宝某东", "good":"今天的购物车会吃得很饱", "bad":"你会剁手", "tag":"其他"},
            {"name":"整理小窝", "good":"整理过后,神清气爽", "bad":"现在的小窝找东西更有效率", "tag":"日常"},
            {"name":"清一下电脑垃圾", "good":"看看又堆了几个G", "bad":"红了再说", "tag":"日常"},
            {"name":"扫一下病毒", "good":"重要性不用我多说了吧", "bad":"浪费CPU，不干", "tag":"日常"},
            {"name":"约朋友出来玩", "good":"今天会玩得很高兴", "bad":"人家没时间", "tag":"社交"},
            {"name":"上Twitter", "good":"关注的同志更新了", "bad":"时间线会被魔怔人占领", "tag":"社交"},
            {"name":"上Pixiv", "good":"今天又有很多好图", "bad":"今天的图很没意思", "tag":"ACGNer"},
            {"name":"看Discord", "good":"群友的聊天很精彩", "bad":"群友聊的不关你事", "tag":"社交"},
            {"name":"看看你不经常看的群聊", "good":"群友的聊天很精彩", "bad":"群友聊的不关你事", "tag":"社交"},
            {"name":"去泡个澡", "good":"你有多少天没有洗澡了", "bad":"洗澡在浪费你的时间", "tag":"日常"},
            {"name":"去散个步", "good":"你会发现你从未发现的景象", "bad":"你会很快疲惫", "tag":"日常"},
            {"name":"去骑单车", "good":"你会骑得很爽", "bad":"今天的红灯挺多", "tag":"日常"},
            {"name":"找个景点玩玩", "good":"找到的景点人少风景又美", "bad":"景点人挺多的,还贵", "tag":"日常"},
            {"name":"穿可爱的衣服", "good":"今天的你也是如此可爱~", "bad":"会被不应该发现的人发现", "tag":"ACGNer"},
        ]

        self.special_festival_events = [
            {"Date":"L01.01", "name":"换新衣", "good":"当然是穿漂亮衣服辣", "bad":None},
            {"Date":"L01.01", "name":"走亲访友", "good":"听说会有大红包", "bad":None},
            {"Date":"L01.01", "name":"行花街", "good":"行行花街,睇睇春花", "bad":None},
            {"Date":"L01.01", "name":"回看拜年祭视频", "good":"不管是大规模的还是民间的,开心就好", "bad":None},
            {"Date":"L01.01", "name":"讨红包", "good":"今日获得的红包翻倍噢", "bad":None},
            {"Date":"L01.15", "name":"来口元宵", "good":"一口下去，全是传统和怀恋", "bad":None},
            {"Date":"L05.05", "name":"来口粽子", "good":"自己包的说不定更好吃", "bad":None},
            {"Date":"L12.30", "name":"吃年夜饭", "good":"无论身在何处，希望你可以能够和你所爱的欢度今宵", "bad":None},
            {"Date":"06.01", "name":"像个孩子一样", "good":"有多久没有像个孩子一样天真，憧憬未来了", "bad":None},
            {"Date":"06.07", "name":"语文高考", "good":"你的作文立意一定会很准确！", "bad":None},
            {"Date":"06.07", "name":"数学高考", "good":"你答对的所有基础题可以让你上985", "bad":None},
            {"Date":"06.08", "name":"英语高考", "good":"除了大小作文，你只扣个位数的分", "bad":None},
            {"Date":"06.08", "name":"物理&历史高考", "good":"考你都会的知识点", "bad":None},
            {"Date":"06.09", "name":"四小科高考", "good":"选择全对，大题全满分！", "bad":None},
            {"Date":"07.21", "name":"Ciallo ~ (∠・ω< )⌒☆", "good":"无论如何，今天就是这样一个日子嘛", "bad":None},
            {"Date":"08.31", "name":"写作业", "good":"创造奇迹", "bad":"反正都写不完，不如开摆"},
            {"Date":"09.01", "name":"思乡", "good":"妈妈，我要回家", "bad":None},
            {"Date":"11.01", "name":"Trick or Treat", "good":"搞怪，讨糖果", "bad":None},
            {"Date":"12.25", "name":"过圣诞", "good":"Cosplay,送礼物,吃个大餐", "bad":None},
            {"Date":"12.31", "name":"回头想想这一年", "good":"发生的事情还是挺多的，用纸和笔记录下来吧", "bad":None},
        ]

        self.normal_festival_event = {"name": "出去玩", "good": "难得放假，出去散个步也好", "bad": "节日人多，景点贵，还是在家好"}
        self.normal_festival_date_list = ["01.01", "05.01", "10.01"]

    def what_is_todays_fortune(self):
        total_probability = sum(f["probability"] for f in self.fortunes)
        r = random.uniform(0, total_probability)
        for fortune in self.fortunes:
            if r < fortune["probability"]:
                return fortune["name"]
            r -= fortune["probability"]

    def get_festival_fortune(self):
        today = datetime.now()
        month_day = f"{today.month:02d}.{today.day:02d}"

        festival_events_list = []
        for event in self.special_festival_events:
            if event["Date"].startswith("L"):
                # 简化：假设阴历转换同样是公历日期
                festival_date = event["Date"][1:]
            else:
                festival_date = event["Date"]
            
            if festival_date == month_day:
                festival_events_list.append(event)

        if month_day in self.normal_festival_date_list:
            festival_events_list.append(self.normal_festival_event)

        good_event_list = []
        bad_event_list = []
        is_festival = 0

        if festival_events_list:
            festival_event = random.choice(festival_events_list)
            if festival_event["bad"]:
                if random.random() > 0.6:
                    good_event_list.append(festival_event)
                    is_festival = 1
                else:
                    bad_event_list.append(festival_event)
                    is_festival = -1
            else:
                good_event_list.append(festival_event)
                is_festival = 1
        
        return good_event_list, bad_event_list, is_festival

    def extract_events(self, good_count, bad_count, is_festival):
        good_event_list, bad_event_list, _ = self.get_festival_fortune()
        
        if is_festival == 1:
            good_count -= 1
        elif is_festival == -1:
            bad_count -= 1
        
        available_events = self.events.copy()
        for _ in range(good_count):
            event = random.choice(available_events)
            good_event_list.append(event)
            available_events.remove(event)
        
        for _ in range(bad_count):
            event = random.choice(available_events)
            if event["bad"] is None:
                continue
            bad_event_list.append(event)
            available_events.remove(event)

        return good_event_list, bad_event_list

    def what_is_todays_fortune_event(self):
        fortune = self.what_is_todays_fortune()
        if fortune == "大吉":
            return self.extract_events(4, 0, 1)
        elif fortune == "中吉":
            return self.extract_events(3, 1, 1)
        elif fortune == "小吉":
            return self.extract_events(2, 2, 1)
        elif fortune == "不太吉":
            return self.extract_events(1, 3, 1)


class MyClient(botpy.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.NOTIFICATION_CHANNEL_ID = "679321509"
        self.CHAT_CHANNEL_ID = "679328087"
        self.config = Config()
        self.model:BasicModel = importlib.import_module(f"llm.{self.config.LLM_MODEL_LOADER}").llm()
        self.model.load(self.config.LLM_MODEL_PATH, self.config.LLM_ADAPTER_PATH, self.config.LLM_SYSTEM_PROMPT, self.config.LLM_AUTO_SYSTEM_PROMPT, self.config.LLM_EXTRA_ARGS)
        self.LiveStatus = False

    async def on_at_message_create(self, message: Message):
        content = message.content
        content = content.replace(f'<@!{message.mentions[0].id}> ', '')
        message_reference = Reference(message_id=message.id)
        botpy.logger.info(f'content: {content}')
        if content == '/运行状态':
            respond = f'机器人服务：正常\n大语言模型服务：正常\n直播框架运行状态：{'进行中' if self.LiveStatus else '停止'}'
        elif content == '/今日运势':
            fortune_teller = FortuneTeller()
            today_fortune = fortune_teller.what_is_todays_fortune()
            good_events, bad_events = fortune_teller.what_is_todays_fortune_event()
            respond = f"沐雪今日运势：{today_fortune}\n宜：{'、'.join([event['name'] for event in good_events])}\n忌：{'、'.join([event['name'] for event in bad_events])}"
        elif content == '/每日金句':
            respond = self.model.ask('今日金句是？', history=[])
        else:
            respond = self.model.ask(content, history=[])
        await self.api.post_message(channel_id=message.channel_id, content=respond, msg_id=message.id, message_reference=message_reference) 

    async def LiveStartNotification(self):
        await self.api.post_message(channel_id=self.NOTIFICATION_CHANNEL_ID, content="沐雪的直播开始啦！欢迎大家来看哦！")

    async def LiveErrorNotification(self):
        await self.api.post_message(channel_id=self.NOTIFICATION_CHANNEL_ID, content="我看起来撞到哪里了，有人帮我通知一下沐沐吗？")

@app.get("/start")
async def start():
    global client
    config = Config()
    intents = botpy.Intents(public_guild_messages=True, guilds=True, guild_message_reactions=True, guild_members=True, interaction=True)
    client = MyClient(intents=intents, log_level=20, log_format="[%(levelname)s/%(name)s] %(message)s", ext_handlers=DEFAULT_FILE_HANDLER)
    asyncio.create_task(client.start(appid=config.BOT_APPID, secret=config.BOT_SECRET))
    return {"status": "running"}

@app.get("/live_start")
async def live_start():
    client.LiveStatus = True
    await client.LiveStartNotification()
    return {"status": "success"}

@app.post("/live_error")
async def live_error():
    await client.LiveErrorNotification()
    return {"status": "success"}

@app.get("/live_stop")
async def live_stop():
    client.LiveStatus = False
    return {"status": "success"}

@app.get("/stop")
async def stop():
    await client.close()
    return {"status": "stopped"}

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8083, workers=1)