# import requests
# from requests.structures import CaseInsensitiveDict
from datetime import datetime, timedelta
# import os
# import smtplib
# import ssl
# from email.message import EmailMessage
import logging
# import json

import databaseHandler
import skyScannerApiHandler
import emailHandler

def main():
    allConfigs = databaseHandler.fetchAllConfigs()
    
    for config in allConfigs:
        logging.info("========================================================")
        logging.info(f"Processing flight: {config.get('header')}")
        apiQuery = skyScannerApiHandler.createAPIquery(config)
        response = skyScannerApiHandler.getAPIresponse(apiQuery)
        try:
            searchForFlightsFittingCriteria(config, response)
        except Exception as e:
            logging.warning(e)
               
# ===================================================
#                 CONFIGURATION
# ===================================================

logging.basicConfig(level=logging.INFO)

# Skyscanner API config
# URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/indicative/search"
# headers = CaseInsensitiveDict()
# headers["x-api-key"]    = "sh428739766321522266746152871799"
# headers["Content-Type"] = "application/x-www-form-urlencoded"

# Configuring email notification service
# EMAIL_SENDER        = os.getenv('GMAIL_ADDRESS')
# EMAIL_PASSWORD      = os.getenv('GMAIL_PASSWORD')
# MONGO_PASSWORD      = os.getenv('MONGO_PASSWORD')
# context             = ssl.create_default_context()

# ===================================================
#         FETCHING DATA FROM SKYSCANNER API
# ===================================================

# Curl command parsing.
# def createAPIquery(config):
    
#     query = {
#         "query": {
#             "market": "",
#             "locale": "",
#             "currency": "",
#             "queryLegs": [
#             ]
#         }
#     }
    
#     # If locale ain't configured - pick default one (UK, en-GB, EUR)
#     try:
#         query["query"]["market"] = config["locale"]["market"]
#         query["query"]["locale"] = config["locale"]["locale"]
#         query["query"]["currency"] = config["locale"]["currency"]
#     except:
#         query["query"]["market"] = "UK"
#         query["query"]["locale"] = "en-GB"
#         query["query"]["currency"] = "EUR"
        
#     query["query"]["queryLegs"].append(insertFlightInfo(config, 0))
    
#     if (config.get("return").lower() == "true"):
#         query["query"]["queryLegs"].append(insertFlightInfo(config, 1))
    
#     if (config.get("isFixed").lower() != "true"):
#         query["query"]["dateTimeGroupingType"] = "DATE_TIME_GROUPING_TYPE_BY_MONTH"
#     else:
#         query["query"]["dateTimeGroupingType"] = "DATE_TIME_GROUPING_TYPE_UNSPECIFIED"

#     return str(json.dumps(query))

# def insertFlightInfo(config, isReturn):
#     # Airports data
#     originIATA =            config.get("originAirportIATA") or None
#     destinationIATA =       config.get("destinationAirportIATA") or None

#     if (isReturn):
#         originIATA, destinationIATA = destinationIATA, originIATA

#     flightInfo = {
#         "originPlace": {
#             "queryPlace": {
#                 "iata": originIATA
#             }
#         },
#         "destinationPlace": {
#             "queryPlace": {
#                 "iata": destinationIATA
#             }
#         }
#     }

#     # Time data
#     if (config.get("isFixed") == "True"):
#         if (isReturn):
#             day     = config["dateReturn"]["day"]
#             month   = config["dateReturn"]["month"]
#             year    = config["dateReturn"]["year"]
#         else:
#             day     = config["date"]["day"]
#             month   = config["date"]["month"]
#             year    = config["date"]["year"]
            
#         flightInfo["fixedDate"] = {
#             "day"   : str(day),
#             "month" : str(month),
#             "year"  : str(year)
#         }
#     else:
#         if (isReturn):
#             monthFrom   = config["dateFromReturn"]["month"]
#             monthTo     = config["dateToReturn"]["month"]
#             yearFrom    = config["dateFromReturn"]["year"]
#             yearTo      = config["dateToReturn"]["year"]
#         else:
#             monthFrom   = config["dateFrom"]["month"]
#             monthTo     = config["dateTo"]["month"]
#             yearFrom    = config["dateFrom"]["year"]
#             yearTo      = config["dateTo"]["year"]
        
#         flightInfo["dateRange"] = {
#             "startDate": {
#                 "month" : str(monthFrom),
#                 "year"  : str(yearFrom)
#             },
#             "endDate": {
#                 "month" : str(monthTo),
#                 "year"  : str(yearTo)
#             }
#         }

#     return flightInfo

# def getAPIresponse(query):
#     try:
#         response = requests.post(URL, headers=headers, data=query)
#         if response.status_code != 200:
#             logging.warning("Failed to download flight information with response code" + str(response.status_code))
#             logging.warning("Query " + query)
#             logging.warning("Response message" + response)
        
#         return response.json()['content']['results']['quotes']

#     except Exception as ex:
#         logging.warning(ex)
#         logging.warning(query)
#         logging.warning(response)

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
            currency = config["locale"]["currency"]
            logging.info(f"No flights found in the given price (up to {config.get('priceNotification')} {currency}). The cheapest flight costs {minPrice} {currency}.")
        else:
            print(f"Flight fits the criteria, the price is {minPrice}")
            emailHandler.sendEmail(bestFittedFlight, config, minPrice)
        
        logging.info(f"Is direct?:     {bestFittedFlight['isDirect']}")
        logging.info(f"Departure from: {bestFittedFlight['outboundLeg']['originPlaceId']}")
        logging.info(f"Arrival to:     {bestFittedFlight['outboundLeg']['destinationPlaceId']}")
        logging.info(f"Departure date: {bestFittedFlight['outboundLeg']['departureDateTime']['year']}-{bestFittedFlight['outboundLeg']['departureDateTime']['month']}-{bestFittedFlight['outboundLeg']['departureDateTime']['day']}")
            
        if config.get("return"):
            logging.info(f"Return from:    {bestFittedFlight['inboundLeg']['originPlaceId']}")
            logging.info(f"Return to:      {bestFittedFlight['inboundLeg']['destinationPlaceId']}")
            logging.info(f"Return date:    {bestFittedFlight['inboundLeg']['departureDateTime']['year']}-{bestFittedFlight['inboundLeg']['departureDateTime']['month']}-{bestFittedFlight['inboundLeg']['departureDateTime']['day']}")
        logging.info("========================================================")
            
        databaseHandler.insertFlightData(config, bestFittedFlight, minPrice)

# def sendEmail(flight, config, minPrice):

#     emailAddress    = config.get("emailNotification").get("emailAddress")
#     additionalInfo  = config.get("emailNotification").get("additionalInfo")
#     currency        = config["locale"]["currency"]
#     market          = config["locale"]["market"]
#     header          = config["header"]
#     isReturn        = config["return"]
#     isDirect        = flight["isDirect"]
#     departureDate   = f"{flight['outboundLeg']['departureDateTime']['year']}-{flight['outboundLeg']['departureDateTime']['month']}-{flight['outboundLeg']['departureDateTime']['day']}"
    
#     subject = ""
#     body    = ""
    
#     if (market == 'pl'):
#         subject = f"[Skychecker] Znaleziono lot - {header}"
        
#         if (isReturn):
#             returnDate = f"{flight['inboundLeg']['departureDateTime']['year']}-{flight['inboundLeg']['departureDateTime']['month']}-{flight['inboundLeg']['departureDateTime']['day']}"
#             returnInfo = f"\nData lotu powrotnego: {returnDate}"
#         else:
#             returnInfo = ""
            
#         if (isDirect):
#             directInfo = "Połączenie bez przesiadek"
#         else:
#             directInfo = "Połączenie zawiera przesiadki"
            
#         body = f"""Znaleziono lot - {header} w cenie {minPrice} {currency}
#         Data wylotu: {departureDate}{returnInfo}
#         {directInfo}
#         """
        
#         if additionalInfo is not None:
#             body += f"\n{additionalInfo}"
    
#     elif (market == "en"):
#         subject = f"[SkyChecker] Found best fitted flight \"{config.get('header')}\"!"

#         body = f"The flight between \"{config.get('header')}\" can now be bought for just {minPrice} {currency}."
#         body += f"\nDeparture date: {flight['outboundLeg']['departureDateTime']['year']}-{flight['outboundLeg']['departureDateTime']['month']}-{flight['outboundLeg']['departureDateTime']['day']}"
#         if config.get("return"):
#             body += f"\nReturn departure date: {flight['inboundLeg']['departureDateTime']['year']}-{flight['inboundLeg']['departureDateTime']['month']}-{flight['inboundLeg']['departureDateTime']['day']}"
#         if flight['isDirect'] == True:
#             body += f"\nThe flight(s) are direct."
#         else:
#             body += f"\nThe flight(s) are NOT direct!"
#         if additionalInfo is not None:
#             body += f"\n{additionalInfo}"
#         body += "\n\nBR //BOT"

#     em = EmailMessage()
#     em['From'] = EMAIL_SENDER
#     em['To'] = emailAddress
#     em['Subject'] = subject
#     em.set_content(body)

#     with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
#         smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
#         smtp.sendmail(EMAIL_SENDER, emailAddress, em.as_string())

# ===================================================
#                EXECUTE SCRIPT
# ===================================================

if __name__ == "__main__":
    main()
