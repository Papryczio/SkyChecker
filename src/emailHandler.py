import logging
import smtplib
import ssl
from email.message import EmailMessage
import os

logging.basicConfig(level=logging.INFO)

EMAIL_SENDER        = os.getenv('GMAIL_ADDRESS')
EMAIL_PASSWORD      = os.getenv('GMAIL_PASSWORD')
MONGO_PASSWORD      = os.getenv('MONGO_PASSWORD')
context             = ssl.create_default_context()

def sendEmail(flight, config, minPrice):

    emailAddress    = config.get("emailNotification").get("emailAddress")
    additionalInfo  = config.get("emailNotification").get("additionalInfo")
    currency        = config["locale"]["currency"]
    market          = config["locale"]["market"]
    header          = config["header"]
    isReturn        = config["return"]
    isDirect        = flight["isDirect"]
    departureDate   = f"{flight['outboundLeg']['departureDateTime']['year']}-{flight['outboundLeg']['departureDateTime']['month']}-{flight['outboundLeg']['departureDateTime']['day']}"
    
    subject = ""
    body    = ""
    
    if (market == 'PL'):
        subject = f"[Skychecker] Znaleziono lot - {header}"
        
        if (isReturn):
            returnDate = f"{flight['inboundLeg']['departureDateTime']['year']}-{flight['inboundLeg']['departureDateTime']['month']}-{flight['inboundLeg']['departureDateTime']['day']}"
            returnInfo = f"\nData lotu powrotnego: {returnDate}"
        else:
            returnInfo = ""
            
        if (isDirect):
            directInfo = "Połączenie bez przesiadek"
        else:
            directInfo = "Połączenie zawiera przesiadki"
            
        body = f"""Znaleziono lot - {header} w cenie {minPrice} {currency}
    Data wylotu: {departureDate}
    {returnInfo}
    {directInfo}
        """
        
        if additionalInfo is not None:
            body += f"\n{additionalInfo}"
    
    elif (market == "EN"):
        subject = f"[SkyChecker] Found best fitted flight \"{config.get('header')}\"!"

        body = f"The flight between \"{config.get('header')}\" can now be bought for just {minPrice} {currency}."
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