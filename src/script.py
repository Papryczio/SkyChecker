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
import logging

# Skyscanner API config
URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/indicative/search"
headers = CaseInsensitiveDict()
headers["x-api-key"] = "sh428739766321522266746152871799"
headers["Content-Type"] = "application/x-www-form-urlencoded"

# Configuring email notification service
EMAIL_SENDER        = os.getenv('GMAIL_ADDRESS')
EMAIL_PASSWORD      = os.getenv('GMAIL_PASSWORD')
MONGO_PASSWORD      = os.getenv('MONGO_PASSWORD')
context             = ssl.create_default_context()

# Configuring database
uri = "mongodb+srv://skyChecker:" + str(MONGO_PASSWORD) + "@skychecker.qjthns8.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri, server_api=ServerApi('1'))

MARKET      = "PL"
LOCALE      = "pl-PL"
CURRENCY    = "PLN"

# Getting all configured flights configurations.
def execute():
    db = client.skyChecker.Configuration
    for config in db.find():
        print(config.get("header"))
        lookForFlightOffers(config)

def lookForFlightOffers(config):
    print("\n========================================================")
    print(f"Processing flight: {config.get('header')}")
    apiQuery = createAPIquery(config)
    getAPIresponse(config, apiQuery)

# Curl command parsing.
def createAPIquery(config):
    query = '{"query":{'
    query += '"market":"' + MARKET + '","locale":"' + LOCALE + '","currency":"' + CURRENCY + '","dateTimeGroupingType":"DATE_TIME_GROUPING_TYPE_BY_DATE","queryLegs":['
    query = insertAirports(config, query, False)
    query = insertDates(config, query, False)
        
    if config.get("return").lower() == "true":
        query += ','
        query = insertAirports(config, query, True)
        query = insertDates(config, query, True)
        query += ']}}'
    print(query)
    return query

def insertAirports(config, query, isReturn):
        originEntityID =        config.get("originAirportEntityID") or None 
        originIATA =            config.get("originAirportIATA") or None
        destinationEntityID =   config.get("destinationAirportEntityID") or None
        destinationIATA =       config.get("destinationAirportIATA") or None
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

def insertDates(config, query, isReturn):
    dayFrom =   str(config.get("dateFromReturn").get("day"))    if isReturn else    str(config["dateFrom"]["day"])
    dayTo =     str(config.get("dateToReturn").get("day"))      if isReturn else    str(config["dateTo"]["day"])
    monthFrom = str(config.get("dateFromReturn").get("month"))  if isReturn else    str(config["dateFrom"]["month"])
    monthTo =   str(config.get("dateToReturn").get("month"))    if isReturn else    str(config["dateTo"]["month"])
    yearFrom =  str(config.get("dateFromReturn").get("year"))   if isReturn else    str(config["dateFrom"]["year"])
    yearTo =    str(config.get("dateToReturn").get("year"))     if isReturn else    str(config["dateTo"]["year"])

    query += '"dateRange":{"startDate":{"day":' + dayFrom + ',"month":' + monthFrom + ',"year":' + yearFrom + '},"endDate":{"day":' + dayTo + ',"month":' + monthTo + ',"year":' + yearTo + '}}}'
    return query

execute()

def getAPIresponse(config, query):
    try:
        response = requests.post(URL, headers=headers, data=query)
        if response.status_code != 200:
            logging.error("Failed to download flight information")
            logging.debug(query)
            logging.debug(response)
        
        flightsInfo = response.json()['content']['results']['quotes']
        
        minPrice = 99999999
        bestFittedFlight = ""
        
        for flightCode in flightsInfo:
            flight = flightsInfo.get(flightCode)

            # In case the flight is return - check max and min days between flights.
            if config.get("return").lower() == "true":
                date = str(flight['outboundLeg']['departureDateTime']['year']) + "-"
                date += str(flight['outboundLeg']['departureDateTime']['month']) + "-"
                date += str(flight['outboundLeg']['departureDateTime']['day'])
                outboundDate = datetime.strptime(date, "%Y-%m-%d")

                date = str(flight['inboundLeg']['departureDateTime']['year']) + "-"
                date += str(flight['inboundLeg']['departureDateTime']['month']) + "-"
                date += str(flight['inboundLeg']['departureDateTime']['day'])
                inboundDate = datetime.strptime(date, "%Y-%m-%d")

                difference = inboundDate - outboundDate
                minDays = timedelta(days=config.get("daysMinimum"))
                maxDays = timedelta(days=config.get("daysMaximum"))

                if(difference < minDays or difference > maxDays):
                    continue

            # Check if the flight is direct or not.
            if (str(flight['isDirect']).lower() != config.get("onlyDirectFlights").lower()):
                continue

            # Check if the flight is cheaper then the cheapest one yet found.
            if(int(flight['minPrice']['amount']) < minPrice):
                bestFittedFlight = flight
                minPrice = int(flight['minPrice']['amount'])

        # Skipping if there are no flights at all, triggering mail if threshold met.
        if minPrice == 999999999:
            logging.info("No flights fitted given criteria.")
            logging.info("========================================================\n")
            return
        elif minPrice > config.get("maxPrice"):
            logging.info(f"No flights found in the given price (up to {config.get('maxPrice')} {CURRENCY}). The cheapest flight costs {minPrice} {CURRENCY}.")
        else:
            print(f"Flight fits the criteria, the price is {minPrice}")
            sendEmail(bestFittedFlight, config, minPrice)

        logging.info(f"Is direct?:     {bestFittedFlight['isDirect']}")
        logging.info(f"Departure from: {bestFittedFlight['outboundLeg']['originPlaceId']}")
        logging.info(f"Arrival to:     {bestFittedFlight['outboundLeg']['destinationPlaceId']}")
        logging.info(f"Departure date: {bestFittedFlight['outboundLeg']['departureDateTime']['year']}-{bestFittedFlight['outboundLeg']['departureDateTime']['month']}-{bestFittedFlight['outboundLeg']['departureDateTime']['day']}")
        if config.get("return"):
            logging.info(f"Return from:    {bestFittedFlight['inboundLeg']['originPlaceId']}")
            logging.info(f"Return to:      {bestFittedFlight['inboundLeg']['destinationPlaceId']}")
            logging.info(f"Return date:    {bestFittedFlight['inboundLeg']['departureDateTime']['year']}-{bestFittedFlight['inboundLeg']['departureDateTime']['month']}-{bestFittedFlight['inboundLeg']['departureDateTime']['day']}")
        logging.info("========================================================\n")

        insertIntoDatabase(config, bestFittedFlight, minPrice)
    except Exception as ex:
        logging.error(ex)
        logging.debug(query)
        logging.debug(response)

def insertIntoDatabase(config, flight, minPrice):
    try:
        db = client.skyChecker.flightData

        insert = {"name": config.get("header"), "from": flight['outboundLeg']['originPlaceId'], "to": flight['outboundLeg']['destinationPlaceId'], "direct": flight['isDirect'], 
            "departure": str(flight['outboundLeg']['departureDateTime']['year']) + "-" + str(flight['outboundLeg']['departureDateTime']['month']) + "-" + str(flight['outboundLeg']['departureDateTime']['day']),
            "price": minPrice, "checkDate": datetime.now()}
        
        if config.get("return"):
            insert["return"] = str(flight['inboundLeg']['departureDateTime']['year']) + "-" + str(flight['inboundLeg']['departureDateTime']['month']) + "-" + str(flight['inboundLeg']['departureDateTime']['day'])
        
        result = db.insert_one(insert)
        logging.debug(result)

    except Exception as ex:
        logging.error(ex)

    
class EmailNotificationParams:
    def __init__(self, config):
        self.emailAddress = config.get("emailAddress")
        self.flightFrom = config.get("flightFrom")
        self.flightTo = config.get("flightTo")
        self.otherInfo = config.get("otherInfo") or None

def sendEmail(flight, config, minPrice):

    emailAddress = config.get("emailNotification").get("emailAddress")
    additionalInfo = config.get("emailNotification").get("additionalInfo")

    subject = f"[SkyChecker] Found best fitted flight \"{config.get('header')}\"!"

    body = f"The flight between \"{config.get('header')}\" can now be bought for just {minPrice} {CURRENCY}."
    body += f"\nDeparture date: {flight['outboundLeg']['departureDateTime']['year']}-{flight['outboundLeg']['departureDateTime']['month']}-{flight['outboundLeg']['departureDateTime']['day']}"
    if flight.returnFlight:
        body += f"\nReturn departure date: {flight['inboundLeg']['departureDateTime']['year']}-{flight['inboundLeg']['departureDateTime']['month']}-{flight['inboundLeg']['departureDateTime']['day']}"
    if flight['isDirect'] == True:
        body += f"\nThe flight(s) are direct."
    else:
        body += f"\nThe flight(s) are NOT direct!"
    if additionalInfo is not None:
        body += f"\n{additionalInfo}"
    body += "\n\nBR //BOT"

    em = EmailMessage()
    em['From'] = EMAIL_SENDER
    em['To'] = emailAddress
    em['Subject'] = subject
    em.set_content(body)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_SENDER, emailAddress, em.as_string())