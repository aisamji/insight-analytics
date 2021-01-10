#! python3
import sys
import argparse
import os

from mailchimp3 import MailChimp
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials


def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('campaign_name')
    parser.add_argument('--to-google-sheet', '-gs', dest='google_sheet')
    ns = parser.parse_args(args)

    mc_client = MailChimp(mc_api='45ef254b0660a24cf859d541e5d1ddd4-us16')
    mc_search_results = mc_client.search_campaigns.get(
        query=ns.campaign_name, fields='results.campaign.id'
        )
    mc_campaign_id = mc_search_results['results'][0]['campaign']['id']

    sa_file = os.path.join(os.path.dirname(__file__), '../google-credentials.json')
    creds = Credentials.from_service_account_file(sa_file, scopes=[
        'https://www.googleapis.com/auth/spreadsheets',
    ])
    gsheet_client = build('sheets', 'v4', credentials=creds)
    append_body = {
        'values': [[ns.campaign_name]]
    }
    gsheet_client.spreadsheets().values().append(
        spreadsheetId=ns.google_sheet,
        range='Master!I11:I16',
        body=append_body,
    ).execute()

    update_ranges = [f'{ns.campaign_name}!B2:B3', f'{ns.campaign_name}!C6:E22']
    mc_report = mc_client.reports.get(campaign_id=mc_campaign_id)
    mc_click_details = mc_client.reports.click_details.all(campaign_id=mc_campaign_id)
    urls_clicked = mc_click_details['urls_clicked']
    update_body = {'data': [
        {
            'range': f'{ns.campaign_name}!B2:B3',
            'values': [[
                mc_report['opens']['open_rate'],
                mc_report['clicks']['click_rate']
            ]],
            'majorDimension': 'COLUMNS',
        },
        {
            'range': f'{ns.campaign_name}!C6:E22',
            'values': [
                [info['url'], info['click_percentage'], info['unique_click_percentage']]
                for info in urls_clicked
            ]
        }
    ]}

    gsheet_client.spreadsheets().values().batchUpdate(
        spreadsheetId=ns.google_sheet,
        body=update_body,
    ).execute()


if __name__ == '__main__':
    main(sys.argv[1:])
