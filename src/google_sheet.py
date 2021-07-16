import json
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import boto3
from utils import logger
import timezones


SSM_CLIENT = boto3.client('ssm')
GOOGLE_SA_JSON = SSM_CLIENT.get_parameter(Name='/insight-analytics/service-account-info', WithDecryption=True)
GOOGLE_SA_INFO = json.loads(GOOGLE_SA_JSON['Parameter']['Value'])
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
]
GOOGLE_CREDS = Credentials.from_service_account_info(GOOGLE_SA_INFO, scopes=SCOPES)

SHEETS_CLIENT = build('sheets', 'v4', credentials=GOOGLE_CREDS)
DRIVE_CLIENT = build('drive', 'v3', credentials=GOOGLE_CREDS)

METRICS_SPREADSHEET_TEMPLATE = '1EoVKoOKPnnykMBK1bumvDWODp7mW9aAtdhE4B2qTgYY'
SPREADSHEET_NAME_FORMAT = '%Y-%m %B'
SHEET_NAME_FORMAT = '%B %-d'
DATETIME_FORMAT = '%B %-d, %Y at %-I:%M %p'

CHART_DATA_SOURCE = 'Master!I11:I16'
OVERVIEW_RANGE_FORMAT = '{}!B1:B3'
URLS_RANGE_FORMAT = '{}!C6:E116'

MAILCHIMP_API_SECRET = SSM_CLIENT.get_parameter(Name='/insight-analytics/mailchimp-api-key', WithDecryption=True)
MAILCHIMP_API_KEY = MAILCHIMP_API_SECRET['Parameter']['Value']


def get_or_create_spreadsheet(spreadsheet_name):
    try:
        query = f'name = {repr(spreadsheet_name)}'
        file = DRIVE_CLIENT.files().list(q=query).execute()['files'][0]
    except IndexError:
        file = create_spreadsheet_from_template(spreadsheet_name)

    return file['id']


def create_spreadsheet_from_template(spreadsheet_name):
    response = DRIVE_CLIENT.files().copy(fileId=METRICS_SPREADSHEET_TEMPLATE, body={'name': spreadsheet_name}).execute()
    fridays = get_all_fridays_for_the_month(datetime.strptime(spreadsheet_name, SPREADSHEET_NAME_FORMAT))
    fridays = list(map(lambda x: x.strftime(SHEET_NAME_FORMAT), fridays))
    string_fridays = list(map(lambda x: f"'{x}", fridays))
    initialize_sheets(response['id'], fridays)
    data = {'values': [string_fridays], 'majorDimension': 'COLUMNS'}
    SHEETS_CLIENT.spreadsheets().values().update(spreadsheetId=response['id'], range=CHART_DATA_SOURCE, body=data, valueInputOption='USER_ENTERED').execute()
    return response


def get_all_fridays_for_the_month(first_day_of_month):
    days_delta = (4 - first_day_of_month.weekday()) % 7
    first_friday = first_day_of_month + timedelta(days=days_delta)
    fridays = []
    selected_friday = first_friday
    while selected_friday.month == first_friday.month:
        fridays.append(selected_friday)
        selected_friday += timedelta(days=7)
    return fridays


def initialize_sheets(spreadsheet_id, fridays):
    spreadsheet_info = SHEETS_CLIENT.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = filter(lambda x: x['properties']['title'].endswith('Friday'), spreadsheet_info['sheets'])

    batch = SheetRequestBatch(spreadsheet_id)
    for sheet in sheets:
        try:
            batch.new_update_request(sheet['properties']['sheetId'], title=fridays.pop(0))
        except IndexError:
            batch.new_delete_request(sheet['properties']['sheetId'])

    batch.execute()


class SheetRequestBatch:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self.requests = []

    def new_update_request(self, sheet_id, **new_properties):
        fields = ' '.join(new_properties.keys())
        self.requests.append({
            'updateSheetProperties': {
                'properties': {
                    'sheetId': sheet_id,
                    **new_properties
                },
                'fields': fields
            }
        })

    def new_delete_request(self, sheet_id):
        self.requests.append({
            'deleteSheet': {
                'sheetId': sheet_id,
            }
        })

    def execute(self):
        SHEETS_CLIENT.spreadsheets().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={'requests': self.requests},
        ).execute()


class CellUpdateRequestBatch:
    def __init__(self, spreadsheet_id, sheet_name):
        self.spreadsheet_id = spreadsheet_id
        self.overview_range = OVERVIEW_RANGE_FORMAT.format(sheet_name)
        self.overview = None
        self.urls_range = URLS_RANGE_FORMAT.format(sheet_name)
        self.urls = None

    def set_overview(self, details):
        values = [(
            datetime.now(tz=timezones.CENTRAL).strftime(DATETIME_FORMAT),
            details['open_rate'],
            details['click_rate']
        )]
        self.overview = {
            'majorDimension': 'COLUMNS',
            'range': self.overview_range,
            'values': values,
        }

    def set_urls(self, url_info):
        values = [
            (u, i['click_rate'], i['unique_click_rate'])
            for u, i in url_info.items()
        ]
        values.sort(key=lambda x: x[1], reverse=True)
        self.urls = {
            'majorDimension': 'ROWS',
            'range': self.urls_range,
            'values': values,
        }

    def execute(self):
        data = []
        if self.overview:
            data.append(self.overview)
        if self.urls:
            data.append(self.urls)
        logger.debug(data)
        SHEETS_CLIENT.spreadsheets().values().batchUpdate(
            spreadsheetId=self.spreadsheet_id,
            body={
                'valueInputOption': 'RAW',
                'data': data
            }
        ).execute()
