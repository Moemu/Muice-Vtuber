import aiosqlite,os,time,asyncio
from llm import Message
from typing import Optional

class Database:
    def __init__(self) -> None:
        self.DB_PATH = 'database.db'
        if not os.path.isfile(self.DB_PATH):
            asyncio.run(self.__create_database())

    def __connect(self) -> aiosqlite.Connection:
        return aiosqlite.connect(self.DB_PATH)
    
    async def __execute(self, query: str, params=(), fetchone=False, fetchall=False) -> list | None:
        """
        异步执行SQL查询，支持可选参数。

        :param query: 要执行的SQL查询语句
        :param params: 传递给查询的参数
        :param fetchone: 是否获取单个结果
        :param fetchall: 是否获取所有结果
        """
        async with self.__connect() as conn:
            cursor = await conn.cursor()
            await cursor.execute(query, params)
            if fetchone:
                return await cursor.fetchone()  # type: ignore
            if fetchall:
                return await cursor.fetchall()  # type: ignore
            await conn.commit()

    async def __create_database(self) -> None:
        """
        初始化数据库
        """
        await self.__execute('''CREATE TABLE CHAT(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            TIME TEXT NOT NULL,
            USERNAME TEXT NOT NULL,
            USERID TEXT NOT NULL,
            DANMU TEXT NOT NULL,
            RESPOND TEXT NOT NULL,
            AVAILABLE INT NOT NULL);''')
        await self.__execute('''CREATE TABLE GIFT(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            TIME TEXT NOT NULL,
            USERNAME TEXT NOT NULL,
            USERID TEXT NOT NULL,
            GIFTNAME TEXT NOT NULL,
            TOTALPRICE NUMERIC NOT NULL);''')
    
    async def add_item(self, username: str, userid: str, danmu: str, respond: str):
        """
        添加一条对话记录
        """
        current_time = time.strftime('%Y.%m.%d %H:%M:%S')
        query = '''INSERT INTO CHAT (TIME, USERNAME, USERID, DANMU, RESPOND) 
                   VALUES (?, ?, ?, ?, ?)'''
        await self.__execute(query, (current_time, username, userid, danmu, respond))
    
    async def add_gift(self, username: str, userid: str, giftname: str, totalprice: float):
        """
        添加一条爆金币记录
        """
        current_time = time.strftime('%Y.%m.%d %H:%M:%S')
        query = '''INSERT INTO GIFT (TIME, USERNAME, USERID, GIFTNAME, TOTALPRICE) 
                   VALUES (?, ?, ?, ?, ?)'''
        await self.__execute(query, (current_time, username, userid, giftname, totalprice))
        
    async def unavailable_item(self, userid:str):
        """
        清空对话历史：将 `AVAILABLE` 历史对话可用标志设 0
        """
        query = "UPDATE CHAT SET AVAILABLE = 0 WHERE USERID = ?"
        await self.__execute(query, (userid,))

    async def get_history(self, userid: Optional[str] = None, limit: Optional[int] = 0) -> list[Message]:
        """
        获取对话历史，返回一个列表

        :userid: (可选) 用户id
        :limit: (可选) 返回的最大长度，当该变量设为0时表示全部返回
        """
        # 根据文档，该函数应支持可选的userid参数，如果不提供则返回所有用户的历史记录
        if userid:
            if limit:
                query = f"SELECT * FROM CHAT WHERE AVAILABLE = 1 AND USERID = ? ORDER BY ID DESC LIMIT {limit}"
            else:
                query = "SELECT * FROM CHAT WHERE AVAILABLE = 1 AND USERID = ?"
            rows = await self.__execute(query, (userid,), fetchall=True)
        else:
            if limit:
                query = f"SELECT * FROM CHAT WHERE AVAILABLE = 1 ORDER BY ID DESC LIMIT {limit}"
            else:
                query = "SELECT * FROM CHAT WHERE AVAILABLE = 1"
            rows = await self.__execute(query, (), fetchall=True)

        return [Message(*row) for row in rows] if rows else []

    async def remove_last_item(self, userid:str):
        """
        撤回指令：移除用户的上一条记录
        """
        query = "DELETE FROM CHAT WHERE ID = (SELECT ID FROM CHAT WHERE USERID = ? ORDER BY ID DESC LIMIT 1)"
        await self.__execute(query, (userid,))