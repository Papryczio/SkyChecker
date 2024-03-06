from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

# Configuring database
MONGO_PASSWORD      = os.getenv('MONGO_PASSWORD')
URI = "mongodb+srv://skycheckerbot:" + str(MONGO_PASSWORD) + "@skychecker.zviwh6x.mongodb.net/?retryWrites=true&w=majority"
CLIENT = MongoClient(URI, server_api=ServerApi('1'))

# ======================
#        METHODS
# ======================

def fetchAllConfigs():
    """
    The function fetches all configurations from the skyChecker database collection.
    :return: The function `fetchAllConfigs()` is attempting to fetch all configurations from a MongoDB
    collection named "Configuration" under the "skyChecker" database. If successful, it will return all
    the documents found in that collection. If an exception occurs during the process, the error will be
    logged using the `logging.error()` function.
    """
    try:
        db = CLIENT.skyChecker.Configuration
        return db.find()
    except Exception as e:
        logging.error(e)

def insertFlightData(config, flight, minPrice):
    """
    The function `insertFlightData` inserts flight data into a MongoDB database based on the provided
    configuration, flight details, and minimum price.
    
    :param config: Config is a dictionary containing configuration settings for the flight data
    insertion process. It includes information such as the header for the database, whether to
    include return flight data, and any other necessary settings for inserting flight data into the
    database
    :param flight: The `flight` parameter in the `insertFlightData` function is a dictionary
    containing flight information. It includes details such as the origin place ID, destination place
    ID, whether the flight is direct, departure date and time, and possibly inbound leg information if
    the configuration specifies a return flight
    :param minPrice: The `minPrice` parameter in the `insertFlightData` function represents the minimum
    price of the flight being inserted into the database. This value is used to store the price
    information for the flight in the database record
    """
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
            "name":         db_name,
            "from":         db_from,
            "to":           db_to,
            "direct":       db_direct, 
            "departure":    db_departure,
            "price":        db_price,
            "checkDate":    db_checkDate
        }

        if config.get("return"):
            insert["return"] = str(flight['inboundLeg']['departureDateTime']['year']) + "-" + str(flight['inboundLeg']['departureDateTime']['month']) + "-" + str(flight['inboundLeg']['departureDateTime']['day'])
        
        result = db.insert_one(insert)
        logging.debug(result)

    except Exception as e:
        logging.error(e)