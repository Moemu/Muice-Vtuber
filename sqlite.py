import sqlite3,os,time

class Database:
    def __init__(self) -> None:
        self.DB_PATH = 'database.db'
        if not os.path.isfile(self.DB_PATH):
            self.__create_database()

    def __connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.DB_PATH)
    
    def __execute(self, query:str, params=(), fetchone=False, fetchall=False):
        '''        
        Executes a given SQL query with optional parameters.
        
        :param query: The SQL query to execute.
        :param params: The parameters to pass to the query.
        :param fetchone: Whether to fetch a single result.
        :param fetchall: Whether to fetch all results.
        '''
        with self.__connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if fetchone:
                return cursor.fetchone()
            if fetchall:
                return cursor.fetchall()
            conn.commit()

    def __create_database(self) -> None:
        self.__execute('''CREATE TABLE CHAT(
            ID INT PRIMARY KEY NOT NULL,
            TIME TEXT NOT NULL,
            USERNAME TEXT NOT NULL,
            USERID TEXT NOT NULL,
            DANMU TEXT NOT NULL,
            RESPOND TEXT NOT NULL,
            AVAILABLE INT NOT NULL);''')
        self.__execute('''CREATE TABLE GIFT(
            ID INT PRIMARY KEY NOT NULL,
            TIME TEXT NOT NULL,
            USERNAME TEXT NOT NULL,
            USERID TEXT NOT NULL,
            GIFTNAME TEXT NOT NULL,
            TOTALPRICE NUMERIC NOT NULL);''')

    def __get_lastest_id(self, table: str = 'CHAT') -> int:
        query = f"SELECT ID FROM {table} ORDER BY ID DESC LIMIT 1"
        result = self.__execute(query, fetchone=True)
        return result[0] if result else 0
    
    def add_item(self, username: str, userid: str, danmu: str, respond: str):
        current_time = time.strftime('%Y.%m.%d %H:%M:%S')
        available_id = self.__get_lastest_id() + 1
        query = '''INSERT INTO CHAT (ID, TIME, USERNAME, USERID, DANMU, RESPOND) 
                   VALUES (?, ?, ?, ?, ?, ?)'''
        self.__execute(query, (available_id, current_time, username, userid, danmu, respond))
    
    def add_gift(self, username: str, userid: str, giftname: str, totalprice: float):
        current_time = time.strftime('%Y.%m.%d %H:%M:%S')
        available_id = self.__get_lastest_id('GIFT') + 1
        query = '''INSERT INTO GIFT (ID, TIME, USERNAME, USERID, GIFTNAME, TOTALPRICE) 
                   VALUES (?, ?, ?, ?, ?, ?)'''
        self.__execute(query, (available_id, current_time, username, userid, giftname, totalprice))
        
    def unavailable_item(self, userid:str):
        query = "UPDATE CHAT SET AVAILABLE = 0 WHERE USERID = ?"
        self.__execute(query, (userid,))

    def get_history(self) -> list:
        query = "SELECT * FROM CHAT WHERE AVAILABLE = 1"
        return self.__execute(query, fetchall=True)

    def remove_last_item(self, userid:str):
        query = "DELETE FROM CHAT WHERE ID = (SELECT ID FROM CHAT WHERE USERID = ? ORDER BY ID DESC LIMIT 1)"
        self.__execute(query, (userid,))