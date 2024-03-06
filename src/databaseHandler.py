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
    try:
        db = CLIENT.skyChecker.Configuration
        return db.find()
    except Exception as e:
        logging.error(e)

def insertFlightData(config, flight, minPrice):
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