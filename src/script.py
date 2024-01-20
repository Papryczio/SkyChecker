import requests
from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta
import os
import smtplib
import ssl
from email.message import EmailMessage
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import logging

def main():
    db = CLIENT.skyChecker.Configuration
    for config in db.find():
        logging.info("========================================================")
        logging.info(f"Processing flight: {config.get('header')}")
        apiQuery = createAPIquery(config)
        response = getAPIresponse(apiQuery)
        try:
            searchForFlightsFittingCriteria(config, response)
        except Exception as e:
            logging.warning(e)
               

# ===================================================
#                 CONFIGURATION
# ===================================================

logging.basicConfig(level=logging.INFO)

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
URI = "mongodb+srv://skycheckerbot:" + str(MONGO_PASSWORD) + "@skychecker.zviwh6x.mongodb.net/?retryWrites=true&w=majority"
CLIENT = MongoClient(URI, server_api=ServerApi('1'))

# Configuration of the currency for flight search
MARKET      = "PL"
LOCALE      = "pl-PL"
CURRENCY    = "PLN"

# ===================================================
#         FETCHING DATA FROM SKYSCANNER API
# ===================================================

# Curl command parsing.
def createAPIquery(config):
    query = '{"query":{'
    query += '"market":"' + MARKET + '","locale":"' + LOCALE + '","currency":"' + CURRENCY + '"'
    if (config.get("isFixed") != "True"):
        query += ',"dateTimeGroupingType":"DATE_TIME_GROUPING_TYPE_BY_DATE"'
    query += ',"queryLegs":['
    query = insertAirportsToQuery(config, query, False)
    query = insertDatesToQuery(config, query, False)
        
    if config.get("return").lower() == "true":
        query += ','
        query = insertAirportsToQuery(config, query, True)
        query = insertDatesToQuery(config, query, True)
        query += ']}}'
    return query

def insertAirportsToQuery(config, query, isReturn):
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

def insertDatesToQuery(config, query, isReturn):
    if (config.get("isFixed") == "True"):
        # Fixed dates (can specify days)
        day =   str(config.get("dateReturn").get("day"))    if isReturn else    str(config["date"]["day"])
        month = str(config.get("dateReturn").get("month"))  if isReturn else    str(config["date"]["month"])
        year =  str(config.get("dateReturn").get("year"))   if isReturn else    str(config["date"]["year"])

        query += '"fixedDate":{"day":' + day + ',"month":' + month + ',"year":' + year + '}}'
    else:
        # Not fixed dated (whole month only, cannot specify days)
        monthFrom = str(config.get("dateFromReturn").get("month"))  if isReturn else    str(config["dateFrom"]["month"])
        monthTo =   str(config.get("dateToReturn").get("month"))    if isReturn else    str(config["dateTo"]["month"])
        yearFrom =  str(config.get("dateFromReturn").get("year"))   if isReturn else    str(config["dateFrom"]["year"])
        yearTo =    str(config.get("dateToReturn").get("year"))     if isReturn else    str(config["dateTo"]["year"])

        query += '"dateRange":{"startDate":{"month":' + monthFrom + ',"year":' + yearFrom + '},"endDate":{"month":' + monthTo + ',"year":' + yearTo + '}}}'
        
    return query

def getAPIresponse(query):
    try:
        response = requests.post(URL, headers=headers, data=query)
        if response.status_code != 200:
            logging.warning("Failed to download flight information")
            logging.debug(query)
            logging.debug(response)
        
        return response.json()['content']['results']['quotes']

    except Exception as ex:
        logging.warning(ex)
        logging.debug(query)
        logging.debug(response)

# ===================================================
#               API RESPONSE ANALYSIS
# ===================================================

def searchForFlightsFittingCriteria(config, flightsInfo):
    minPrice = 99999999
    bestFittedFlight = ""
        
    for flightCode in flightsInfo:
        flight = flightsInfo.get(flightCode)

        # In case the flight is return - check max and min days between flights.
        if (config.get("return").lower() == "true" and config.get("isFixed") != "True"):
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
    if bestFittedFlight == "":
        logging.info("No flights fitted given criteria.")
        logging.info("========================================================")
        return
    else:
        if minPrice > config.get("priceNotification"):
            logging.info(f"No flights found in the given price (up to {config.get('priceNotification')} {CURRENCY}). The cheapest flight costs {minPrice} {CURRENCY}.")
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
        logging.info("========================================================")
            
        insertIntoDatabase(config, bestFittedFlight, minPrice)

# ===================================================
#      DATABASE INSERT AND EMAIL NOTIFICATION
# ===================================================

def insertIntoDatabase(config, flight, minPrice):
    try:
        db = CLIENT.skyChecker.flightData
        
        db_name         = config.get("header")
        db_from         = flight['outboundLeg']['originPlaceId']
        db_to           = flight['outboundLeg']['destinationPlaceId']
        db_direct       = flight['isDirect']
        db_departure    = str(flight['outboundLeg']['departureDateTime']['year']) + "-" + str(flight['outboundLeg']['departureDateTime']['month']) + "-" + str(flight['outboundLeg']['departureDateTime']['day'])
        db_price        = minPrice
        db_checkDate    = datetime.now()

        insert = {
            "name": db_name,
            "from": db_from,
            "to": db_to,
            "direct": db_direct, 
            "departure": db_departure,
            "price": db_price,
            "checkDate": db_checkDate
        }

        if config.get("return"):
            insert["return"] = str(flight['inboundLeg']['departureDateTime']['year']) + "-" + str(flight['inboundLeg']['departureDateTime']['month']) + "-" + str(flight['inboundLeg']['departureDateTime']['day'])
        
        result = db.insert_one(insert)
        logging.debug(result)

    except Exception as ex:
        logging.error(ex)

def sendEmail(flight, config, minPrice):

    emailAddress = config.get("emailNotification").get("emailAddress")
    additionalInfo = config.get("emailNotification").get("additionalInfo")

    subject = f"[SkyChecker] Found best fitted flight \"{config.get('header')}\"!"

    body = f"The flight between \"{config.get('header')}\" can now be bought for just {minPrice} {CURRENCY}."
    body += f"\nDeparture date: {flight['outboundLeg']['departureDateTime']['year']}-{flight['outboundLeg']['departureDateTime']['month']}-{flight['outboundLeg']['departureDateTime']['day']}"
    if config.get("return"):
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

# ===================================================
#                EXECUTE SCRIPT
# ===================================================

if __name__ == "__main__":
    main()
