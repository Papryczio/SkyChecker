import requests
from requests.structures import CaseInsensitiveDict
import json
from datetime import datetime, timedelta
import os

URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/indicative/search"

headers = CaseInsensitiveDict()
headers["x-api-key"] = "prtl6749387986743898559646983194"
headers["Content-Type"] = "application/x-www-form-urlencoded"

# Getting config file.
CURRENT_DIR = os.getcwd()
CONFIG_FILE_PATH = os.path.join(CURRENT_DIR, 'cfg/config.json')
config = ""
with open(CONFIG_FILE_PATH) as file:
    config = json.load(file)

# Getting general job configuration.
class SearchConfiguration: 
    def __init__(self, config):
        self.market =   config.get("market")
        self.locale =   config.get("locale")
        self.currency = config.get("currency")

searchConfig = SearchConfiguration(config["SearchConfiguration"])
print("\n========================================================")
print("                  JOB CONFIGURATION")
print(f"Market:     {searchConfig.market}")
print(f"Locale:     {searchConfig.locale}")
print(f"Currency:   {searchConfig.currency}")
print("========================================================\n")

# Getting all configured flights configurations.
class FlightDate:
    def __init__(self, cfg):
        if cfg is not None:
            self.day =      cfg.get("day")
            self.month =    cfg.get("month")
            self.year =     cfg.get("year")

class FlightConfiguration:
    def __init__(self, config):
        self.originAirportIATA =            config.get("originAirportIATA") or None
        self.originAirportEntityID =        config.get("originAirportEntityID") or None
        self.destinationAirportIATA =       config.get("destinationAirportIATA") or None
        self.destinationAirportEntityID =   config.get("destinationAirportEntityID") or None
        self.dateFrom =                     FlightDate(config.get("dateFrom"))
        self.dateTo =                       FlightDate(config.get("dateTo"))
        self.dateFromReturn =               FlightDate(config.get("dateFromReturn") or None)
        self.dateToReturn =                 FlightDate(config.get("dateToReturn") or None)
        self.daysMinimum =                  config.get("daysMinimum") or None
        self.daysMaximum =                  config.get("daysMaximum") or None
        self.onlyDirectFlights =            config.get("onlyDirectFlights")
        self.returnFlight =                 config.get("return")
        self.maxPrice =                     config.get("maxPrice") or None

for cfg in config["FlightConfiguration"]:
    print(f"Processing flight: {cfg}")
    flightConfig = FlightConfiguration(config["FlightConfiguration"].get(cfg))

    print("\n========================================================")
    print("                  FLIGHT CONFIGURATION")
    print(f"Origin Airport IATA:            {flightConfig.originAirportIATA}")
    print(f"Origin Airport EntityID:        {flightConfig.originAirportEntityID}")
    print(f"Destination Airport IATA:       {flightConfig.destinationAirportIATA}")
    print(f"Destination Airport EntityID:   {flightConfig.destinationAirportEntityID}")
    print(f"Date From:                      {flightConfig.dateFrom.year}-{flightConfig.dateFrom.month}-{flightConfig.dateFrom.day}")
    print(f"Date To:                        {flightConfig.dateTo}-{flightConfig.dateTo.month}-{flightConfig.dateTo.day}")
    print(f"Date From (Return):             {flightConfig.dateFromReturn}-{flightConfig.dateFromReturn.month}-{flightConfig.dateFromReturn.day}")
    print(f"Date To (Return):               {flightConfig.dateToReturn}-{flightConfig.dateToReturn.month}-{flightConfig.dateToReturn.day}")
    print(f"Minimum days:                   {flightConfig.daysMinimum}")
    print(f"Maximum days:                   {flightConfig.daysMaximum}")
    print(f"Direct flights only?:           {flightConfig.onlyDirectFlights}")
    print(f"Return flight?:                 {flightConfig.returnFlight}")
    print("========================================================\n")

    # Curl command parsing.
    def pasteAirports(query, isReturn):
        originEntityID =        flightConfig.originAirportEntityID
        originIATA =            flightConfig.originAirportIATA
        destinationEntityID =   flightConfig.destinationAirportEntityID
        destinationIATA =       flightConfig.destinationAirportIATA
        if isReturn == True:
            originEntityID, destinationEntityID =   destinationEntityID, originEntityID
            originIATA, destinationIATA =           destinationIATA, originIATA

        if originEntityID is None and destinationEntityID is None:
            query += '{"originPlace":{"queryPlace":{"iata":"' + originIATA + '"}},"destinationPlace":{"queryPlace":{"iata":"' + destinationIATA + '"}},'
        elif originEntityID is not None and destinationEntityID is None:
            query += '{"originPlace":{"queryPlace":{"entityId":"' + originEntityID + '"}},"destinationPlace":{"queryPlace":{"iata":"' + destinationIATA + '"}},'
        elif originEntityID is None and destinationEntityID is not None:
            query += '{"originPlace":{"queryPlace":{"iata":"' + originIATA + '"}},"destinationPlace":{"queryPlace":{"entityId":"' + destinationEntityID + '"}},'
        else:
            query += '{"originPlace":{"queryPlace":{"entityId":"' + originEntityID + '"}},"destinationPlace":{"queryPlace":{"entityId":"' + destinationEntityID + '"}},'
        return query

    def pasteDate(query, isReturn):
        dayFrom =   str(flightConfig.dateFromReturn.day)    if isReturn else    str(flightConfig.dateFrom.day)
        dayTo =     str(flightConfig.dateToReturn.day)      if isReturn else    str(flightConfig.dateTo.day)
        monthFrom = str(flightConfig.dateFromReturn.month)  if isReturn else    str(flightConfig.dateFrom.month)
        monthTo =   str(flightConfig.dateToReturn.month)    if isReturn else    str(flightConfig.dateTo.month)
        yearFrom =  str(flightConfig.dateFromReturn.year)   if isReturn else    str(flightConfig.dateFrom.year)
        yearTo =    str(flightConfig.dateToReturn.year)     if isReturn else    str(flightConfig.dateTo.year)

        query += '"dateRange":{"startDate":{"day":' + dayFrom + ',"month":' + monthFrom + ',"year":' + yearFrom + '},"endDate":{"day":' + dayTo + ',"month":' + monthTo + ',"year":' + yearTo + '}}}'
        return query

    query = '{"query":{'
    query += '"market":"' + searchConfig.market + '","locale":"' + searchConfig.locale + '","currency":"' + searchConfig.currency + '","dateTimeGroupingType":"DATE_TIME_GROUPING_TYPE_BY_DATE","queryLegs":['
    query = pasteAirports(query, False)
    query = pasteDate(query, False)
    if flightConfig.returnFlight.lower() == "true":
        query += ','
        query = pasteAirports(query, True)
        query = pasteDate(query, True)
    query += ']}}'

    # Executing CuRL.
    resp = requests.post(URL, headers=headers, data=query)
    flightsInfo = resp.json()['content']['results']['quotes']

    # Get best fitted flight
    minPrice = 999999999
    bestFittedFlight = ""

    for json in flightsInfo:
        flight = flightsInfo.get(json)
        # --- Check if flight matches user's criteria. ---
        # Time delta between outbound and inbound
        if flightConfig.returnFlight.lower() == "true":
            date = str(flight['outboundLeg']['departureDateTime']['year']) + "-"
            date += str(flight['outboundLeg']['departureDateTime']['month']) + "-"
            date += str(flight['outboundLeg']['departureDateTime']['day'])
            outboundDate = datetime.strptime(date, "%Y-%m-%d")

            date = str(flight['inboundLeg']['departureDateTime']['year']) + "-"
            date += str(flight['inboundLeg']['departureDateTime']['month']) + "-"
            date += str(flight['inboundLeg']['departureDateTime']['day'])
            inboundDate = datetime.strptime(date, "%Y-%m-%d")

            difference = inboundDate - outboundDate
            minDays = timedelta(days=flightConfig.daysMinimum)
            maxDays = timedelta(days=flightConfig.daysMaximum)

            if(difference < minDays or difference > maxDays):
                continue

        # Check if the flight is direct or not.
        if(str(flight['isDirect']).lower() != flightConfig.onlyDirectFlights.lower()):
            continue

        # --- Check if the flight is cheaper than the cheapest yet found. ---
        if(int(flight['minPrice']['amount']) < minPrice):
            bestFittedFlight = flight
            minPrice = int(flight['minPrice']['amount'])


    if minPrice == 999999999:
        print("INFO: No flights fitted given criteria.")
    elif minPrice > flightConfig.maxPrice:
        print(f"INFO: No flights found in the given price (up to {flightConfig.maxPrice} {searchConfig.currency}). The cheapest flight costs {minPrice} {searchConfig.currency}.")
    else:
        print(f"INFO: Flight fits the criteria, the price is {minPrice}")
