class MailChimp:

    def __init__(self, mc_api):
        self._api_key = mc_api

    @property
    def search_campaigns(self):
        return SearchCampaigns()

    @property
    def reports(self):
        return Reports()


class SearchCampaigns:
    def get(self, *, query, fields=None):
        matches = filter(lambda x: query in x['campaign']['title'], _campaigns)
        return {'results': list(matches)}


class Reports:
    @property
    def click_details(self):
        return ReportClickDetails()

    def get(self, *, campaign_id, fields=None):
        return _reports


class ReportClickDetails:
    def all(self, *, campaign_id, fields=None):
        return _click_details


_campaigns = [
    {
        'campaign': {
            'title': 'Test1',
            'id': 'test1'
        }
    },
    {
        'campaign': {
            'title': 'Test2',
            'id': 'test2'
        }
    },
]
_reports = {
    'opens': {'open_rate': 0.245646},
    'clicks': {'click_rate': 0.012345},
}
_click_details = {
    'urls_clicked': [
        {
            'url': 'https://the.ismaili/usa',
            'click_percentage': 0.23475,
            'unique_click_percentage': 0.01021
        },
        {
            'url': 'https://www.youtube.com/',
            'click_percentage': 0.40020,
            'unique_click_percentage': 0.02931
        },
    ]
}
