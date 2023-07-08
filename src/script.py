import requests
from requests.structures import CaseInsensitiveDict
import json
from datetime import datetime, timedelta
import os
import smtplib
import ssl
from email.message import EmailMessage
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Skyscanner API config
URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/indicative/search"
headers = CaseInsensitiveDict()
headers["x-api-key"] = "sh428739766321522266746152871799"
headers["Content-Type"] = "application/x-www-form-urlencoded"

# Getting config file.
CURRENT_DIR = os.getcwd()
CONFIG_FILE_PATH = os.path.join(CURRENT_DIR, 'cfg/config.json')
config = ""
with open(CONFIG_FILE_PATH) as file:
    config = json.load(file)

# Configuring email notification service
EMAIL_SENDER =      os.getenv('GMAIL_ADDRESS')
EMAIL_PASSWORD =    os.getenv('GMAIL_PASSWORD')
context = ssl.create_default_context()

# Configuring database
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')
uri = "mongodb+srv://skyChecker:" + str(MONGO_PASSWORD) + "@skychecker.qjthns8.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    print(client.list_database_names())
except Exception as e:
    print(e)
    print("dupa")

# Getting general job configuration.
class SearchConfiguration: 
    def __init__(self, config):
        self.market =   config.get("market")
        self.locale =   config.get("locale")
        self.currency = config.get("currency")

searchConfig = SearchConfiguration(config["SearchConfiguration"])

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

class EmailNotificationParams:
    def __init__(self, config):
        self.emailAddress = config.get("emailAddress")
        self.flightFrom = config.get("flightFrom")
        self.flightTo = config.get("flightTo")
        self.otherInfo = config.get("otherInfo") or None

def sendEmail(bestFittedFlight, flightConfig, searchConfig):

    emailParams = EmailNotificationParams(config["FlightConfiguration"].get(cfg)["emailNotification"])

    subject = f"[SkyChecker] Found best fitted flight from {emailParams.flightFrom} to {emailParams.flightTo}!"

    body = f"The flight between {emailParams.flightFrom} and {emailParams.flightTo} can now be bought for just {minPrice} {searchConfig.currency}."
    body += f"\nDeparture date: {bestFittedFlight['outboundLeg']['departureDateTime']['year']}-{bestFittedFlight['outboundLeg']['departureDateTime']['month']}-{bestFittedFlight['outboundLeg']['departureDateTime']['day']}"
    if flightConfig.returnFlight:
        body += f"\nReturn departure date: {bestFittedFlight['inboundLeg']['departureDateTime']['year']}-{bestFittedFlight['inboundLeg']['departureDateTime']['month']}-{bestFittedFlight['inboundLeg']['departureDateTime']['day']}"
    if bestFittedFlight['isDirect'] == True:
        body += f"\nThe flight(s) are direct."
    else:
        body += f"\nThe flight(s) are NOT direct!"
    if emailParams.otherInfo is not None:
        body += f"\n{emailParams.otherInfo}"
    body += "\n\nBR //BOT"

    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = emailParams.emailAddress
    em['Subject'] = subject
    em.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_SENDER, emailParams.emailAddress, em.as_string())

for cfg in config["FlightConfiguration"]:
    print("\n========================================================")
    print(f"Processing flight: {cfg}")
    flightConfig = FlightConfiguration(config["FlightConfiguration"].get(cfg))

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

    print(query)

    try:
        # Executing CuRL.
        resp = requests.post(URL, headers=headers, data=query)
        if resp.status_code != 200:
            print("[ERROR] Failed to download flight information.")
        flightsInfo = resp.json()['content']['results']['quotes']

        # Get best fitted flight
        minPrice = 999999999
        bestFittedFlight = ""

        for flightCode in flightsInfo:
            flight = flightsInfo.get(flightCode)

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
            print("No flights fitted given criteria.")
            print("========================================================\n")
            continue
        elif minPrice > flightConfig.maxPrice:
            print(f"No flights found in the given price (up to {flightConfig.maxPrice} {searchConfig.currency}). The cheapest flight costs {minPrice} {searchConfig.currency}.")
        else:
            print(f"Flight fits the criteria, the price is {minPrice}")
            sendEmail(bestFittedFlight, flightConfig, searchConfig)
        
        print(f"Is direct?:     {bestFittedFlight['isDirect']}")
        print(f"Departure from: {bestFittedFlight['outboundLeg']['originPlaceId']}")
        print(f"Arrival to:     {bestFittedFlight['outboundLeg']['destinationPlaceId']}")
        print(f"Departure date: {bestFittedFlight['outboundLeg']['departureDateTime']['year']}-{bestFittedFlight['outboundLeg']['departureDateTime']['month']}-{bestFittedFlight['outboundLeg']['departureDateTime']['day']}")
        if flightConfig.returnFlight:
            print(f"Return from:    {bestFittedFlight['inboundLeg']['originPlaceId']}")
            print(f"Return to:      {bestFittedFlight['inboundLeg']['destinationPlaceId']}")
            print(f"Return date:    {bestFittedFlight['inboundLeg']['departureDateTime']['year']}-{bestFittedFlight['inboundLeg']['departureDateTime']['month']}-{bestFittedFlight['inboundLeg']['departureDateTime']['day']}")
        print("========================================================\n")
    except Exception as ex:
        print(ex)
        print(resp)