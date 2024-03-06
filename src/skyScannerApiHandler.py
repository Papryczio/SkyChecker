import logging
import requests
from requests.structures import CaseInsensitiveDict
import json

logging.basicConfig(level=logging.INFO)

URL = "https://partners.api.skyscanner.net/apiservices/v3/flights/indicative/search"
headers = CaseInsensitiveDict()
headers["x-api-key"]    = "sh428739766321522266746152871799"
headers["Content-Type"] = "application/x-www-form-urlencoded"

# ======================
#        METHODS
# ======================

def createAPIquery(config):
    """
    The function `createAPIquery` generates an API query based on the provided configuration, with
    default values if certain configuration parameters are missing.
    
    :param config: The `config` parameter in the `createAPIquery` function is a dictionary
    containing configuration settings for creating an API query. The function constructs an API query
    based on the provided configuration
    :return: The `createAPIquery` function returns a JSON string representation of a query object based
    on the provided `config` input. The query object includes information about market, locale,
    currency, flight legs, and dateTimeGroupingType based on the configuration provided.
    """
    
    query = {
        "query": {
            "market": "",
            "locale": "",
            "currency": "",
            "queryLegs": [
            ]
        }
    }
    
    # If locale ain't configured - pick default one (UK, en-GB, EUR)
    try:
        query["query"]["market"] = config["locale"]["market"]
        query["query"]["locale"] = config["locale"]["locale"]
        query["query"]["currency"] = config["locale"]["currency"]
    except:
        query["query"]["market"] = "UK"
        query["query"]["locale"] = "en-GB"
        query["query"]["currency"] = "EUR"
        
    query["query"]["queryLegs"].append(insertFlightInfo(config, 0))
    
    if (config.get("return").lower() == "true"):
        query["query"]["queryLegs"].append(insertFlightInfo(config, 1))
    
    if (config.get("isFixed").lower() != "true"):
        query["query"]["dateTimeGroupingType"] = "DATE_TIME_GROUPING_TYPE_BY_MONTH"
    else:
        query["query"]["dateTimeGroupingType"] = "DATE_TIME_GROUPING_TYPE_UNSPECIFIED"

    return str(json.dumps(query))

def insertFlightInfo(config, isReturn):
    """
    The function `insertFlightInfo` takes in configuration data and a flag indicating return flight,
    then constructs and returns a dictionary containing flight information based on the input data.
    
    :param config: The `config` parameter in the `insertFlightInfo` function is a dictionary containing
    information related to flight details and dates. It includes keys such as "originAirportIATA",
    "destinationAirportIATA", "isFixed", "date", "dateReturn", "dateFrom", "dateTo
    :param isReturn: The `isReturn` parameter in the `insertFlightInfo` function is a boolean flag that
    indicates whether the flight information being inserted is for a return trip or not. If `isReturn`
    is `True`, it means the flight information is for a return trip, and if it's `False
    :return: The function `insertFlightInfo` returns a dictionary containing flight information based on
    the provided configuration and whether it is for a return flight or not. The dictionary includes
    details such as origin and destination airports, as well as either a fixed date or a date range
    depending on the configuration settings.
    """
    
    # Airports data
    originIATA =            config.get("originAirportIATA") or None
    destinationIATA =       config.get("destinationAirportIATA") or None

    if (isReturn):
        originIATA, destinationIATA = destinationIATA, originIATA

    flightInfo = {
        "originPlace": {
            "queryPlace": {
                "iata": originIATA
            }
        },
        "destinationPlace": {
            "queryPlace": {
                "iata": destinationIATA
            }
        }
    }

    # Time data
    if (config.get("isFixed") == "True"):
        if (isReturn):
            day     = config["dateReturn"]["day"]
            month   = config["dateReturn"]["month"]
            year    = config["dateReturn"]["year"]
        else:
            day     = config["date"]["day"]
            month   = config["date"]["month"]
            year    = config["date"]["year"]
            
        flightInfo["fixedDate"] = {
            "day"   : str(day),
            "month" : str(month),
            "year"  : str(year)
        }
    else:
        if (isReturn):
            monthFrom   = config["dateFromReturn"]["month"]
            monthTo     = config["dateToReturn"]["month"]
            yearFrom    = config["dateFromReturn"]["year"]
            yearTo      = config["dateToReturn"]["year"]
        else:
            monthFrom   = config["dateFrom"]["month"]
            monthTo     = config["dateTo"]["month"]
            yearFrom    = config["dateFrom"]["year"]
            yearTo      = config["dateTo"]["year"]
        
        flightInfo["dateRange"] = {
            "startDate": {
                "month" : str(monthFrom),
                "year"  : str(yearFrom)
            },
            "endDate": {
                "month" : str(monthTo),
                "year"  : str(yearTo)
            }
        }

    return flightInfo

def getAPIresponse(query):
    """
    The function `getAPIresponse` sends a POST request to a URL with headers and data, handles errors,
    and returns flight information from the response in JSON format.
    
    :param query: The `getAPIresponse` function is making a POST request to a URL
    with some headers and data. It then checks the response status code and logs warnings if it's not
    200. Finally, it tries to return a specific part of the JSON response
    :return: The function is attempting to make a POST request to a specified URL with headers and data
    provided in the query parameter. If the response status code is not 200, it logs a warning message
    with details of the failure.
    """
    
    try:
        response = requests.post(URL, headers=headers, data=query)
        if response.status_code != 200:
            logging.warning("Failed to download flight information with response code" + str(response.status_code))
            logging.warning("Query " + query)
            logging.warning("Response message" + response)
        
        return response.json()['content']['results']['quotes']

    except Exception as ex:
        logging.warning(ex)
        logging.warning(query)
        logging.warning(response)