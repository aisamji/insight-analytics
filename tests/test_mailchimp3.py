from pytest import param, mark, fixture
from mailchimp3 import MailChimp

client = MailChimp(mc_api='0123456789abcdef0123456789abcdef-us16')


@fixture(scope='module')
def report():
    return client.reports.get(campaign_id='947a654248')


@fixture(scope='module')
def click_details():
    return client.reports.click_details.all(campaign_id='947a654248')


@mark.parametrize('name', (
    'Friday January 8 2021 AIS',
    param('FridayX', marks=mark.xfail),
))
def test_get_campaign_id_by_name(name):
    response = client.search_campaigns.get(query=name, fields='results.campaign.id')
    results = response['results']
    assert 1 == len(results) and type(results[0]['campaign']['id']) is str


def test_get_open_rate(report):
    open_rate = report['opens']['open_rate']
    assert type(open_rate) is float


def test_get_click_rate(report):
    click_rate = report['clicks']['click_rate']
    assert type(click_rate) is float


def test_get_link_information(click_details):
    urls_clicked = click_details['urls_clicked']
    assert type(urls_clicked) is list


def test_get_link_url(click_details):
    urls_clicked = click_details['urls_clicked']
    assert type(urls_clicked[0]['url']) is str


def test_get_link_click_rate(click_details):
    urls_clicked = click_details['urls_clicked']
    assert type(urls_clicked[0]['click_percentage']) is float


def test_get_link_unique_click_rate(click_details):
    urls_clicked = click_details['urls_clicked']
    assert type(urls_clicked[0]['unique_click_percentage']) is float
