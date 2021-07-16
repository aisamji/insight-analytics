from collections import defaultdict
from datetime import datetime, timedelta
from io import BytesIO
import tarfile
import json
import requests
from mailchimp3 import MailChimp
from utils import with_backoff, with_backoff_condition, logger
from google_sheet import get_or_create_spreadsheet, CellUpdateRequestBatch, MAILCHIMP_API_KEY

GSHEET_TEMPLATE_ID = '1EoVKoOKPnnykMBK1bumvDWODp7mW9aAtdhE4B2qTgYY'


mc_client = None


def main():
    campaign_name, spreadsheet_name, sheet_name = extrapolate_vars()
    logger.info(f'Extracting metrics from {repr(campaign_name)}.')
    campaign_id = find_campaign_id(campaign_name)
    logger.info(f'Mailchimp Campaign Id: {campaign_id}')
    click_details = get_click_details(campaign_id)
    url_link_ids = group_links_by_url(campaign_id)
    url_details = get_clicks_by_url(campaign_id, url_link_ids)
    url_click_info = get_url_click_rates(url_details, click_details)

    spreadsheet_id = get_or_create_spreadsheet(spreadsheet_name)
    logger.info(f'Saving data to Spreadsheet {repr(spreadsheet_name)} — {spreadsheet_id}')
    batch = CellUpdateRequestBatch(spreadsheet_id, sheet_name)
    batch.set_overview(click_details)
    batch.set_urls(url_click_info)
    batch.execute()


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
    for url, link_ids in url_link_ids.items():
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
        response_info = BytesIO(requests.get(actual_location).content)
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
        mc_client = MailChimp(mc_api=MAILCHIMP_API_KEY)
    return mc_client


def get_url_click_rates(url_details, overall_details):
    data = {
        u: {
            'click_rate': d['total']/overall_details['total_clicks'],
            'unique_click_rate': d['unique']/overall_details['unique_clicks'],
        }
        for u, d in url_details.items()
    }
    logger.debug(data)
    return data


if __name__ == '__main__':
    main()
