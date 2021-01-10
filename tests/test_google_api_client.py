import os

from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from pytest import fixture

sa_file = os.path.join(os.path.dirname(__file__), '../google-credentials.json')
creds = Credentials.from_service_account_file(sa_file, scopes=[
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
])


@fixture(scope='module')
def gsheet_client():
    return build('sheets', 'v4', credentials=creds)


@fixture(scope='module')
def temp_gsheet(gsheet_client):
    spreadsheet = gsheet_client.spreadsheets().create().execute()
    sid = spreadsheet['spreadsheetId']
    yield sid
    gdrive_client = build('drive', 'v3', credentials=creds)
    gdrive_client.files().delete(fileId=sid).execute()


def test_read_spreadsheet_ranges(gsheet_client):
    sid = '1QZTRXfSvr-rcF-q9qOhO0-iYYrH2FiL62utBtExwOLo'
    sranges = ['My Pokemon!A1:A2', 'My Pokemon!C1:C2', 'My Pokemon!E1:E2']
    expected = [
        [['Mankey/Primeape', 'Vital Spirit']],
        [['Rattata/Raticate', 'Guts']],
        [['Geodude/Graveler/Golem', 'Sturdy']],
    ]
    actual = gsheet_client.spreadsheets().values().batchGet(
        spreadsheetId=sid,
        ranges=sranges,
        majorDimension='COLUMNS'
    ).execute()['valueRanges']
    assert (expected[0] == actual[0]['values']
            and expected[1] == actual[1]['values']
            and expected[2] == actual[2]['values'])


def test_write_spreadsheet_ranges(gsheet_client, temp_gsheet):
    smods = {
        'Sheet1!A1:B2': [
            ['Nobody', 'Knows'],
            ['The', 'Sorrow']],
    }
    data = {'data': [{'range': r, 'values': v} for r, v in smods.items()]}
    data['valueInputOption'] = 'USER_ENTERED'
    gsheet_client.spreadsheets().values().batchUpdate(
        spreadsheetId=temp_gsheet,
        body=data
        ).execute()
    result = gsheet_client.spreadsheets().values().get(
        spreadsheetId=temp_gsheet,
        range='Sheet1!B1'
        ).execute()
    assert [['Knows']] == result['values']


def test_append_to_range(gsheet_client, temp_gsheet):
    body = {
        'values': [
            ['A', 'B'],
            ['C', '']
        ]
    }
    gsheet_client.spreadsheets().values().update(
        spreadsheetId=temp_gsheet,
        range='Sheet1!C1:D2',
        valueInputOption='USER_ENTERED',
        body=body
        ).execute()

    body2 = {
        'values': [['D', 'F']]
    }
    gsheet_client.spreadsheets().values().append(
        spreadsheetId=temp_gsheet,
        range='Sheet1!C:D',
        valueInputOption='USER_ENTERED',
        body=body2
        ).execute()
    result = gsheet_client.spreadsheets().values().get(
        spreadsheetId=temp_gsheet,
        range='Sheet1!C3:D3'
        ).execute()
    assert [['D', 'F']] == result['values']
