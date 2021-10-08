import sqlite3
import os
from psycopg2 import connect
import datetime
from google_module import GoogleSheets, GoogleDocs, GoogleDocsRead
from tqdm import tqdm


def get_date_time():
    offset = datetime.timedelta(hours=3)
    dt = datetime.datetime.now(tz=datetime.timezone(offset, 'МСК'))
    date = f'{dt.date().day}.{dt.date().month}.{dt.date().year}'
    time = f'{dt.time().hour}:{dt.time().minute}:{dt.time().second}'
    return date, time


if os.environ.get('HEROKU') == "True":
    DATABASE_URL = os.environ['DATABASE_URL']
    sslmode = 'require'
    params = {'dsn': DATABASE_URL, 'sslmode': 'require'}
else:
    import config
    DATABASE = config.DATABASE
    DATABASE_USER = config.DATABASE_USER
    DATABASE_PASSWORD = config.DATABASE_PASSWORD
    DATABASE_HOST = config.DATABASE_HOST
    DATABASE_PORT = config.DATABASE_PORT
    params = {'database': config.DATABASE, 'user': config.DATABASE_USER, 'password': config.DATABASE_PASSWORD,
              'host': config.DATABASE_HOST, 'port': config.DATABASE_PORT}


with sqlite3.connect('data.db',  check_same_thread=False) as db:
    cursor = db.cursor()


def get_data(table):
    data = []
    data_list = cursor.execute(f"""SELECT * FROM {table}""")
    for item in data_list:
        data.append(item)
    return data


def get_instruction(field, table):
    data = []
    data_list = cursor.execute(f"""SELECT {field} FROM {table}""")
    for item in data_list:
        data.append(item)
    return data


class DataBaseFunctions:

    @staticmethod
    def insert_data_in_base_by_token(data, table_name):
        with connect(**params) as conn:
            cur = conn.cursor()
            for item in data:
                cur.execute(f'''INSERT INTO {table_name} VALUES {item[1]}''')
            print('data was written')

    @staticmethod
    def insert_user(data, table_name):
        with connect(**params) as conn:
            cur = conn.cursor()
            cur.execute("""INSERT INTO %s VALUES %s""" % (table_name, data))

    @staticmethod
    def select_data(table_name: str):
        with connect(**params) as conn:
            cur = conn.cursor()
            cur.execute(f'''SELECT * FROM {table_name}''')
            data = cur.fetchall()
            print(data)
            return data

    @staticmethod
    def recreate_table(table_name: str):
        with connect(**params) as conn:
            print('connection establish')
            cur = conn.cursor()
            cur.execute('''DROP TABLE %s''' % table_name)
            print('table deleted')
            cur.execute('''CREATE TABLE requests 
                         (REQUEST_TOKEN TEXT PRIMARY KEY NOT NULL UNIQUE,
                         USER_ID TEXT NOT NULL,
                         PATH TEXT NOT NULL,
                         END_POINT TEXT NOT NULL,
                         DATE TEXT NOT NULL,
                         TIME TEXT NOT NULL,
                         RATING TEXT NOT NULL);''')
            print('table created')

    @staticmethod
    def create_table_request():
        with connect(**params) as conn:
            print('connection establish')
            cur = conn.cursor()
            cur.execute('''CREATE TABLE requests 
                     (REQUEST_TOKEN TEXT PRIMARY KEY NOT NULL UNIQUE,
                     USER_ID TEXT FOREING KEY,
                     PATH TEXT NOT NULL,
                     END_POINT TEXT NOT NULL,
                     DATE TEXT NOT NULL,
                     TIME TEXT NOT NULL,
                     RATING TEXT NOT NULL);''')
            print('table created')

    @staticmethod
    def create_table(sql_params: str):
        with connect(**params) as conn:
            print('connection establish')
            cur = conn.cursor()
            cur.execute('''%s;''' % sql_params)
            print('table created')

    @staticmethod
    def drop_table(table_name: str):
        with connect(**params) as conn:
            print('connection establish')
            cur = conn.cursor()
            cur.execute('''DROP TABLE %s''' % table_name)
            print('table deleted')

    @staticmethod
    def update_instruction_rating(data):
        with connect(**params) as conn:
            cur = conn.cursor()
            for item in data:
                cur.execute(f'''UPDATE requests 
                                SET rating = %s 
                                WHERE request_token = %s''', (item[1][6], item[0]))
                print(f'request data with token {item[0]} was updated')


class ImportFunction:

    @staticmethod
    def import_in_google_sheet(sheet_url: str, spreadsheet_name: str, table_name: str):
        try:
            data = DataBaseFunctions.select_data(table_name)
            GoogleSheets(sheet_url).add_interaction(spreadsheet_name=spreadsheet_name, values=data)
            DataBaseFunctions.recreate_table(table_name)
        except Exception as e:
            print(e)

    @staticmethod
    def import_user_in_google_sheet(sheet_url: str, spreadsheet_name: str, table_name: str):
        try:
            data = DataBaseFunctions.select_data(table_name)
            GoogleSheets(sheet_url).clear_table(spreadsheet_name=spreadsheet_name)
            GoogleSheets(sheet_url).add_interaction(spreadsheet_name=spreadsheet_name, values=data)
        except Exception as e:
            print(e)


class DataCash:

    def __init__(self, life_time=20):
        self.values = []
        self.create_time = get_date_time()
        self.life_time = life_time

    def add_value(self, value):
        self.values.append(value)
        return self.values


class UnmarkedRequestCash(DataCash):

    def write_values(self, table_name, max_count_element=20):
        if len(self.values) >= max_count_element:
            DataBaseFunctions.insert_data_in_base_by_token(self.values, table_name)
            self.values = []
        else:
            pass


class MarkedRequestCash(DataCash):

    def update_instruction_rating(self, max_count_element=20):
        if len(self.values) >= max_count_element:
            DataBaseFunctions.update_instruction_rating(self.values)
            self.values = []
        else:
            pass


class SheetCash(DataCash):

    def get_tags(self):
       return self.values[0][10:6]


class InstructionCash(DataCash):

    def create_cash(self, instruction_link_list):
        pbar = tqdm(instruction_link_list)
        pbar.colour = 'white'
        for item in pbar:
            doc = GoogleDocs(item)
            total_list_item = GoogleDocsRead(doc_body=doc.get_document_body(), inline_objects=doc.get_inline_object()
                                             ).join_total_list()
            self.add_value(total_list_item)
        pbar.close()
        print("Instruction cash is ready")

    def update_cash(self, data):
        self.values = []
        self.values.append(data)

    def update_cash_unit(self, index, instriction_link_list):
        try:
            doc = GoogleDocs(instriction_link_list[index])
            self.values[index] = GoogleDocsRead(doc_body=doc.get_document_body(), inline_objects=doc.get_inline_object()
                                                 ).join_total_list()
        except Exception as e:
            print("Ошибка обновления ссылок: %s" % e)


if __name__ == "__main__":
    pass
    #print(get_instruction('link', 'instruction'))
    #DataBaseFunctions.drop_table('users')
    #DataBaseFunctions.create_table('CREATE TABLE users (USER_ID TEXT PRIMARY KEY NOT NULL UNIQUE, USER_NAME TEXT, EMAIL TEXT NOT NULL , STATUS TEXT NOT NULL)')
    ImportFunction.import_in_google_sheet(config.LINK_URL_SHEETS_2, 'База обращений', 'requests')
    ImportFunction.import_user_in_google_sheet(config.LINK_URL_SHEETS_2, 'База пользователей', 'users')
    #DataBaseFunctions.select_data('users')











