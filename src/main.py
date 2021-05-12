from collections import defaultdict
import os
import logging
from datetime import datetime, timedelta
from time import sleep
from urllib.request import urlopen
from io import BytesIO
import tarfile
import json
from functools import wraps

from mailchimp3 import MailChimp
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import requests

DEFAULT_TIMEOUT = 10
GSHEET_TEMPLATE_ID = '1EoVKoOKPnnykMBK1bumvDWODp7mW9aAtdhE4B2qTgYY'

old_send = requests.Session.send


def new_send(*args, **kwargs):
    if kwargs.get("timeout", None) is None:
        kwargs["timeout"] = DEFAULT_TIMEOUT
    return old_send(*args, **kwargs)


requests.Session.send = new_send


mc_client = None
gs_client = None
gd_client = None

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
logger.addHandler(handler)


def with_backoff(func):
    return with_backoff_condition('True')(func)


def with_backoff_condition(condition):
    def backoff(func):
        @wraps(func)
        def try_request(*args, **kwargs):
            backoff = 5
            response = None
            while True:
                try:
                    response = func(*args, **kwargs)
                    if eval(condition):
                        break
                except requests.exceptions.ConnectTimeout:
                    pass
                logger.info(f'Retrying request in {backoff} seconds.')
                sleep(backoff)
                backoff *= 2
            return response
        return try_request
    return backoff


def main():
    campaign_name, spreadsheet_name, sheet_name = extrapolate_vars()
    logger.info(f'Extracting metrics from {repr(campaign_name)}.')
    campaign_id = find_campaign_id(campaign_name)
    logger.info(f'Mailchimp Campaign Id: {campaign_id}')
    click_details = get_click_details(campaign_id)
    url_link_ids = group_links_by_url(campaign_id)
    url_details = get_clicks_by_url(campaign_id, url_link_ids)
    url_sheet_data = prepare_url_details_for_gsheet(url_details, click_details)

    spreadsheet_id = get_spreadsheet_id(spreadsheet_name)
    update_sheet(spreadsheet_id, sheet_name, click_details, url_sheet_data)


def update_sheet(spreadsheet_id, sheet_name, click_details, url_sheet_data):
    overall_stats = [(datetime.now().strftime('%B %-d, %Y at %-I:%M %p'), click_details['open_rate'], click_details['click_rate'])]
    # TODO: datetime.now should be in Central timezone not whatever is local
    gsheet_client().spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body={'valueInputOption': 'RAW', 'data': [
        {
            'majorDimension': 'COLUMNS',
            'range': f'{sheet_name}!B1:B3',
            'values': overall_stats,
        },
        {
            'majorDimension': 'ROWS',
            'range': f'{sheet_name}!C6:E116',
            'values': url_sheet_data
        },
    ]}).execute()


def extrapolate_vars():
    today = datetime.today()
    delta_to_last_friday = timedelta(days=(today.weekday() - 4) % 7)
    friday = today - delta_to_last_friday
    return friday.strftime('Friday %B %-d %Y'), friday.strftime('%Y-%m %B'), friday.strftime('%B %-d')


@with_backoff
def find_campaign_id(search_query):
    search_results = mailchimp_client().search_campaigns.get(
        query=search_query, fields='results.campaign.id'
        )
    return search_results['results'][0]['campaign']['id']


@with_backoff
def get_click_details(campaign_id):
    report = mailchimp_client().reports.get(
        campaign_id=campaign_id,
        fields='opens,clicks',
    )
    return {
        'open_rate': report['opens']['open_rate'],
        'click_rate': report['clicks']['click_rate'],
        'total_clicks': report['clicks']['clicks_total'],
        'unique_clicks': report['clicks']['unique_clicks'],
    }


@with_backoff
def group_links_by_url(campaign_id):
    report = mailchimp_client().reports.click_details.all(
        campaign_id=campaign_id,
        fields='urls_clicked.id,urls_clicked.url',
        count=500,
    )
    url_links = defaultdict(list)
    for info in report['urls_clicked']:
        url_links[info['url']].append(info['id'])
    return url_links


def get_clicks_by_url(campaign_id, url_link_ids):
    url_clicks = defaultdict(lambda: {'total': 0, 'unique': set()})
    url_batches = {}
    for url, link_ids in list(url_link_ids.items())[:2]:
        operations = []
        for lid in link_ids:
            operations.append({
                'method': 'GET',
                'path': f'/reports/{campaign_id}/click-details/{lid}/members',
                'params': {'count': 500}
            })
        batch = create_batch({'operations': operations})
        url_batches[url] = batch['id']

    logger.debug(url_batches)

    for url, batch_id in url_batches.items():
        response = get_batch(batch_id)
        actual_location = response['response_body_url']
        response_info = BytesIO(urlopen(actual_location).read())
        tfile = tarfile.open(fileobj=response_info)
        for i in tfile.getmembers():
            f = tfile.extractfile(i)
            if not isinstance(f, tarfile.ExFileObject):
                continue
            data = json.loads(f.read())
            if len(data) > 0 and 'response' in data[0]:
                info = json.loads(data[0]['response'])
                for m in info['members']:
                    url_clicks[url]['total'] += m['clicks']
                    url_clicks[url]['unique'].add(m['email_address'])
        url_clicks[url]['unique'] = len(url_clicks[url]['unique'])
    logger.debug(url_clicks)
    return url_clicks


@with_backoff
def create_batch(data):
    return mailchimp_client().batches.create(data)


@with_backoff_condition('response["response_body_url"] != ""')
def get_batch(batch_id):
    return mailchimp_client().batches.get(batch_id)


def mailchimp_client():
    global mc_client
    if mc_client is None:
        mc_client = MailChimp(mc_api='45ef254b0660a24cf859d541e5d1ddd4-us16')
    return mc_client


def prepare_url_details_for_gsheet(url_details, overall_details):
    data = []
    for url, clicks in url_details.items():
        data.append(
            (
                url,
                clicks['total']/overall_details['total_clicks'],
                clicks['unique']/overall_details['unique_clicks']
            )
        )
    data.sort(key=lambda x: x[1], reverse=True)
    logger.debug(data)
    return data


def get_spreadsheet_id(spreadsheet_name):
    try:
        file = gdrive_client().files().list(q=f'name = {repr(spreadsheet_name)}').execute()['files'][0]
    except IndexError:
        file = create_spreadsheet_from_template(spreadsheet_name)

    return file['id']


def create_spreadsheet_from_template(spreadsheet_name):
    response = gdrive_client().files().copy(fileId=GSHEET_TEMPLATE_ID, body={'name': spreadsheet_name}).execute()
    fridays = get_all_fridays_for_the_month(datetime.strptime(spreadsheet_name, '%Y-%m %B'))
    fridays = list(map(lambda x: x.strftime('%B %-d'), fridays))
    string_fridays = list(map(lambda x: f"'{x}", fridays))
    initialize_sheets(response['id'], fridays)
    data = {'values': [string_fridays], 'majorDimension': 'COLUMNS'}
    gsheet_client().spreadsheets().values().update(spreadsheetId=response['id'], range='Master!I11:I16', body=data, valueInputOption='USER_ENTERED').execute()
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
    spreadsheet_info = gsheet_client().spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = filter(lambda x: x['properties']['title'].endswith('Friday'), spreadsheet_info['sheets'])

    requests = []
    for sheet in sheets:
        try:
            requests.append(
                {
                    'updateSheetProperties': {
                        'properties': {
                            'sheetId': sheet['properties']['sheetId'],
                            'title': fridays.pop(0),
                        },
                        'fields': 'title'
                    }
                }
            )
        except IndexError:
            requests.append(
                {
                    'deleteSheet': {
                        'sheetId': sheet['properties']['sheetId']
                    }
                }
            )
    logger.debug(requests)

    gsheet_client().spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body={'requests': requests}).execute()


def gsheet_client():
    global gs_client
    if gs_client is None:
        sa_file = os.path.join(
            os.path.dirname(__file__),
            '../google-credentials.json'
            )
        creds = Credentials.from_service_account_file(sa_file, scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
        ])
        gs_client = build('sheets', 'v4', credentials=creds)
    return gs_client


def gdrive_client():
    global gd_client
    if gd_client is None:
        sa_file = os.path.join(
            os.path.dirname(__file__),
            '../google-credentials.json'
            )
        creds = Credentials.from_service_account_file(sa_file, scopes=[
            'https://www.googleapis.com/auth/drive',
        ])
        gd_client = build('drive', 'v3', credentials=creds)
    return gd_client


if __name__ == '__main__':
    main()
