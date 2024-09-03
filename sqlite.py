import sqlite3,os,time

class Database:
    def __init__(self) -> None:
        self.connection = sqlite3.connect('database.db')
        self.cursor = self.connection.cursor()
        if not os.path.isfile('database.db'):
            self.__create_database()

    def __create_database(self) -> None:
        self.cursor.execute('''CREATE TABLE CHAT(
            ID INT PRIMARY KEY NOT NULL,
            TIME TEXT NOT NULL,
            USERNAME TEXT NOT NULL,
            USERID INT NOT NULL,
            DANMU TEXT NOT NULL,
            RESPOND TEXT NOT NULL);''')
        self.connection.commit()

    def __get_lastest_id(self) -> int:
        data_cursor = self.cursor.execute('''SELECT * FROM CHAT ORDER BY ID DESC LIMIT 1''')
        lastest_id = 0
        for data in data_cursor:
            lastest_id = data[0]
        return lastest_id
    
    def add_item(self, Username:str, Userid:int, Danmu:str, respond:str):
        current_time = time.strftime('%Y.%m.%d %H:%M:%S')
        available_id = self.__get_lastest_id() + 1
        self.cursor.execute(f'''INSERT INTO CHAT VALUES ({available_id}, '{current_time}', '{Username}', {Userid}, '{Danmu}', '{respond}');''')
        self.connection.commit()

    def get_history(self) -> list:
        data_cursor = self.cursor.execute('''SELECT * FROM CHAT''')
        history = []
        for data in data_cursor:
            history.append([data[4],data[5]])
        return history