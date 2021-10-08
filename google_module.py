import httplib2
import googleapiclient.discovery
from oauth2client.service_account import ServiceAccountCredentials
from collections import defaultdict
import os


def create_keyfile_dict():
    variables_keys = {
        "type": os.environ.get("TYPE"),
        "project_id": os.environ.get("PROJECT_ID"),
        "private_key_id": os.environ.get("PRIVATE_KEY_ID"),
        "private_key": os.environ.get("PRIVATE_KEY"),
        "client_email": os.environ.get("CLIENT_EMAIL"),
        "client_id": os.environ.get("CLIENT_ID"),
        "auth_uri": os.environ.get("AUTH_URI"),
        "token_uri": os.environ.get("TOKEN_URI"),
        "auth_provider_x509_cert_url": os.environ.get("AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.environ.get("CLIENT_X509_CERT_URL")
    }
    return variables_keys


HEROKU = os.environ.get('HEROKU')
scope = ['https://www.googleapis.com/auth/drive',
         'https://www.googleapis.com/auth/documents.readonly', 'https://www.googleapis.com/auth/spreadsheets']
if HEROKU == "True":
    CREDENTIALS_FILE = create_keyfile_dict()
    credentional = ServiceAccountCredentials.from_json_keyfile_dict(
        CREDENTIALS_FILE,
        scope
    )

else:
    from config import CREDENTIONAL_FILE_NAME
    CREDENTIALS_FILE = CREDENTIONAL_FILE_NAME
    credentional = ServiceAccountCredentials.from_json_keyfile_name(
        CREDENTIALS_FILE,
        scope
    )

httpAuth = credentional.authorize(httplib2.Http())
services = googleapiclient.discovery.build('docs', 'v1', http=httpAuth)
services_sheet = googleapiclient.discovery.build('sheets', 'v4', http=httpAuth)


class GoogleDocs:

    # Класс который получает необходимые блоки гугл документа для дальнейшей работы в другом классе
    def __init__(self, link_url):
        self.link_url = link_url

    def get_document_from_url(self):
        docs_id = self.link_url.split('/')[5]
        document = services.documents().get(documentId=docs_id).execute()
        return document

    def get_document_body(self):
        doc_body = self.get_document_from_url().get('body')
        return doc_body

    def get_inline_object(self):
        inline_object = self.get_document_from_url().get('inlineObjects')
        return inline_object


class GoogleDocsRead:

    def __init__(self, doc_body=None, inline_objects=None, document_style=None, named_styles=None,
                 revision_id=None, suggestions_view_mode=None, document_id=None):

        self.doc_body = doc_body
        self.document_style = document_style
        self.inline_objects = inline_objects
        self.named_styles = named_styles
        self.revision_id = revision_id
        self.suggestions_view_mode = suggestions_view_mode
        self.document_id = document_id

    @staticmethod
    def build_in_html(text, styles):
        # print(styles)
        if 'italic' in styles:
            text = f'<i>{text}</i>'
        if 'bold' in styles:
            text = f'<b>{text}</b>'
        if 'underline' in styles:
            text = f'<u>{text}</u>'
        return text

    def read_text(self):
        # print(str(docBody['content'][2]['paragraph']['elements'][1]))

        paragraph_count = int(str(self.doc_body).count('paragraph') / 2)
        total_text_list = []

        for i in range(1, paragraph_count + 1, 1):
            string = ''
            elements_count = len(list(self.doc_body['content'][i]['paragraph']['elements']))

            for j in range(0, elements_count, 1):
                if str(self.doc_body['content'][i]['paragraph']['elements'][j]).count("inlineObjectElement") == 0:
                    text = self.doc_body['content'][i]['paragraph']['elements'][j]['textRun']['content']
                    styles = self.doc_body['content'][i]['paragraph']['elements'][j]['textRun']['textStyle']
                    string = string + self.build_in_html(text=text, styles=styles)
            total_text_list.append(string.replace('\n', ''))

            # if '' in total_text_list:
            # total_text_list.remove('')

        # print(total_text_list)

        return total_text_list

    def get_img(self):

        paragraph_count = int(str(self.doc_body).count('paragraph') / 2)
        total_img_list = []

        for i in range(1, paragraph_count + 1, 1):
            img_url = ''
            elements_count = len(list(self.doc_body['content'][i]['paragraph']['elements']))

            for j in range(0, elements_count, 1):
                if str(self.doc_body['content'][i]['paragraph']['elements'][j]).count("inlineObjectElement") != 0:
                    img_id = self.doc_body['content'][i]['paragraph']['elements'][j]['inlineObjectElement'] \
                        ['inlineObjectId']
                    img_url = (self.inline_objects[f'{img_id}']['inlineObjectProperties']['embeddedObject']
                    ['imageProperties']['contentUri'])

            total_img_list.append(img_url.replace('\n', ''))

            # if '' in total_img_list:
            # total_img_list.remove('')

        # print(total_img_list)

        return total_img_list

    def join_total_list(self):
        text_list = self.read_text()
        img_list = self.get_img()

        index_empty_text = defaultdict(list)
        index_empty_url = defaultdict(list)

        for index, e in enumerate(text_list):
            index_empty_text[e].append(index)

        for index, e in enumerate(img_list):
            index_empty_url[e].append(index)

        total_list = []
        for i in range(len(text_list)):
            total_list.append(text_list[i])
            total_list.append(img_list[i])
            if '' in total_list:
                total_list.remove('')
        if '' in total_list:
            total_list.remove('')

        for i in range(len(total_list)):
            if '' in total_list:
                total_list.remove('')

        '''
        print(index_empty_text)
        print(index_empty_url)

        print(index_empty_text[''])
        print(index_empty_url[''])
        '''
        # print(total_list)

        return total_list


class GoogleSheets:

    def __init__(self, link_url):
        self.link_url = link_url

    def get_sheets_from_url(self):
        sheet_id = self.link_url.split('/')[5]
        return sheet_id

    def add_interaction(self, values, spreadsheet_name):

        '''
        function write data in chosen google sheet's list
        :param values: list in list example: [[variable_1, variable_2 ... variable_N]]
        :param spreadsheet_name: google sheet's list name
        :return:
        '''

        sheet = services_sheet.spreadsheets()
        request = sheet.values().append(spreadsheetId=self.get_sheets_from_url(), range=f'{spreadsheet_name}!A2',
                                        valueInputOption='USER_ENTERED', insertDataOption='INSERT_ROWS',
                                        body={'values': values})
        request.execute()

    def get_sheets_values(self, spreadsheets_name: str, start_row='', end_row='', start_column='A',
                          end_column='ZZ', fields='', valueRenderOption='FORMATTED_VALUE'):
        '''
        :param spreadsheets_name:
        :param start_row: 1,2,3...N
        :param end_row: 1,2,3...N
        :param start_column: A,B,C...
        :param end_column: A,B,C...
        :return: all data in preassigned range. [[value_row 1_column A,
        value_row 2_column B... value_row N_column N][]...]
        '''

        sheet = services_sheet.spreadsheets()
        result = sheet.values().get(spreadsheetId=self.get_sheets_from_url(),
                                    range=f'{spreadsheets_name}!{start_column}{start_row}:{end_column}{end_row}',
                                    valueRenderOption=valueRenderOption, fields=fields)
        request = result.execute()
        sheet_values = request.get('values', [])

        return sheet_values

    def get_spreadsheet(self, spreadsheets_name, start_row='', end_row='', start_column='A',
                                    end_column='ZZ', fields='', param=''):
        sheet = services_sheet.spreadsheets()
        result = sheet.get(spreadsheetId=self.get_sheets_from_url(),
                                    ranges=f'{spreadsheets_name}!{start_column}{start_row}:{end_column}{end_row}',
                                     fields=fields)
        request = result.execute()
        value = request['sheets'][0]['data'][0]['rowData']
        values = []
        for item in value:
            try:
                values.append(item['values'][0][param])
            except KeyError:
                values.append('Нет ссылки')
        return values, request

    @staticmethod
    def get_data_from_base(element_id, base_data, dict_param):
        parameters = base_data
        id_list = []
        for item in parameters:
            id_list.append(item[f'{dict_param}'])
        try:
            index = id_list.index(str(element_id))
            return parameters[index], int(index), id_list
        except ValueError:
            return "Данных нет в базе", id_list

    def add_user_in_base(self, spacial_data, user_id, user_name, spreadsheets_name, email, values):
        assert type(user_id) is str, "Id пользователя должен быть в формате строки"
        sheet = services_sheet.spreadsheets()
        if spacial_data[0] == "Данных нет в базе":
            if 'Empty value' in spacial_data[1]:
                index = spacial_data[1].index('Empty value') + 2
                print(f'Пользователь записан в строку: {index}')
            else:
                index = len(values) + 2
                print(f'Пользователь записан в строку: {index}')
            request = sheet.values().update(spreadsheetId=self.get_sheets_from_url(),
                                            range=f'{spreadsheets_name}!A{index}',
                                            valueInputOption='USER_ENTERED',
                                            body={'values': [[user_id, user_name, f"{email}"]]})
            request.execute()

    def add_rating_instruction(self, instruction_data, spreadsheet_name, effective):
        if instruction_data[0] == 'Данных нет в базе':
            pass
        else:
            instruction_data[0]['rating'] = 'Положительная' if effective else 'Отрицательная'
            sheet = services_sheet.spreadsheets()
            values = [DictWorker.get_massive_from_dict(instruction_data[0])]
            index = instruction_data[1] + 2
            request = sheet.values().update(spreadsheetId=self.get_sheets_from_url(), range=f'{spreadsheet_name}!A{index}',
                                            valueInputOption='USER_ENTERED',
                                            body={'values': values})
            request.execute()

    def clear_table(self, spreadsheet_name):
        sheet = services_sheet.spreadsheets()
        values = self.get_sheets_values(spreadsheet_name, start_row='2')
        new_values = [['' for _ in item] for item in values]
        request = sheet.values().update(spreadsheetId=self.get_sheets_from_url(),
                                        range=f'{spreadsheet_name}!A2',
                                        valueInputOption='USER_ENTERED',
                                        body={'values': new_values})
        request.execute()


class DictWorker:

    @staticmethod
    def get_massive_from_dict(dictionary: dict):
        return [dictionary[key] for key, value in dictionary.items()]

    @staticmethod
    def generate_dict_from_list_and_dict(data_list: list, dictionary: dict):

        '''
        :param data_list:
        :param dictionary:
        :return:
        '''

        assert type(dictionary) is dict, "dictionary должен быть словарем"
        assert type(data_list) is list, 'values должен быть списком'
        dict_list = []
        for item in data_list:
            new_dictionary = {key: value for key, value in dictionary.items()}
            if item:
                i = 0
                for key, value in new_dictionary.items():
                    new_dictionary[key] = item[i]
                    i += 1
            dict_list.append(new_dictionary)

        return dict_list

    @staticmethod
    def generate_dict(keys, values):

        '''
        :param keys: list of keys [1,2,3 ... N]
        :param values: list in list example: [[variable_1, variable_2 ... variable_N]]
        :return: [{dict_1}, {dict_2} ... {dict_N}]
        '''

        return [{keys[i]: item for i, item in enumerate(value)} for value in values]

    @staticmethod
    def find_elements_in_dicts_list(key: str, values: list):

        '''
        :param key: string
        :param keys: list of keys [1,2,3 ... N]
        :param values: list in list example: [{},{},{}]
        :return: string
        '''
        keys = list(values[0].keys())
        assert key in keys, f"Ключа нет в списке доступных ключей. Доступные ключи {keys}"
        assert type(key) is str and type(keys) is list, "Несоответсвие типов данных"
        for item in values:
            assert type(item) is dict, "Item должен быть с типом данных dict"
            try:
                print("%s, %s" % (key,item[key]))
            except KeyError:
                print('Такого ключа нет')

    @staticmethod
    def filter_list_of_dicts(key: str, value: str, data: list[dict]):
        keys = list(data[0].keys())
        assert key in keys, f"Ключа нет в списке доступных ключей. Доступные ключи {keys}"
        assert type(key) is str and type(keys) is list, "Несоответсвие типов данных"
        return list(filter(lambda item: item[key] == value, data))


if __name__ == "__main__":
    import config
    GoogleSheets(config.LINK_URL_SHEETS).clear_table('База пользователей')





