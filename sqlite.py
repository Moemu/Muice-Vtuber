import sqlite3,os,time

class Database:
    def __init__(self) -> None:
        if not os.path.isfile('database.db'):
            self.__create_database()

    def __create_database(self) -> None:
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute('''CREATE TABLE CHAT(
            ID INT PRIMARY KEY NOT NULL,
            TIME TEXT NOT NULL,
            USERNAME TEXT NOT NULL,
            USERID INT NOT NULL,
            DANMU TEXT NOT NULL,
            RESPOND TEXT NOT NULL);''')
        connection.commit()
        connection.close()

    def __get_lastest_id(self) -> int:
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        data_cursor = cursor.execute('''SELECT * FROM CHAT ORDER BY ID DESC LIMIT 1''')
        lastest_id = 0
        for data in data_cursor:
            lastest_id = data[0]
        connection.close()
        return lastest_id
    
    def add_item(self, Username:str, Userid:int, Danmu:str, respond:str):
        current_time = time.strftime('%Y.%m.%d %H:%M:%S')
        available_id = self.__get_lastest_id() + 1
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        cursor.execute(f'''INSERT INTO CHAT VALUES ({available_id}, '{current_time}', '{Username}', {Userid}, '{Danmu}', '{respond}');''')
        connection.commit()
        connection.close()

    def get_history(self) -> list:
        connection = sqlite3.connect('database.db')
        cursor = connection.cursor()
        data_cursor = cursor.execute('''SELECT * FROM CHAT''')
        history = []
        for data in data_cursor:
            history.append([data[4],data[5]])
        connection.close()
        return history