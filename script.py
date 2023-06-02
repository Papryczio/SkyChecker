import requests
from requests.structures import CaseInsensitiveDict
import json

URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/indicative/search"

headers = CaseInsensitiveDict()
headers["x-api-key"] = "prtl6749387986743898559646983194"
headers["Content-Type"] = "application/x-www-form-urlencoded"

class SearchConfiguration:
    def __init__(self, market, locale, currency):
        self.market = market
        self.locale = locale
        self.currency = currency

searchConfig = SearchConfiguration("PL", "pl-PL", "PLN")

data = '{"query":{"market":"' + searchConfig.market + '","locale":"' + searchConfig.locale + '","currency":"' + searchConfig.currency + '","dateTimeGroupingType":"DATE_TIME_GROUPING_TYPE_BY_DATE","queryLegs":[{"originPlace":{"queryPlace":{"iata":"WMI"}},"destinationPlace":{"queryPlace":{"iata":"MLA"}},"dateRange":{"startDate":{"month":10,"year":2023},"endDate":{"month":10,"year":2023}}},{"originPlace":{"queryPlace":{"iata":"MLA"}},"destinationPlace":{"queryPlace":{"iata":"WMI"}},"dateRange":{"startDate":{"month":10,"year":2023},"endDate":{"month":10,"year":2023}}}]}}'
query = ''
resp = requests.post(URL, headers=headers, data=data)

flightInfo = resp.json()['content']['results']['quotes']

for json in flightInfo:
    print(flightInfo.get(json))