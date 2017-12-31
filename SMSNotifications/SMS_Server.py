# /usr/bin/env python
# Download the twilio-python library from twilio.com/docs/libraries/python
import logging
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from SMSNotifications.GdaxClient import GdaxClient
from SMSNotifications.TwilioInformation import TwilioInformation

app = Flask(__name__)
last_message = 'There was no Last Command'

gdax_client = GdaxClient()

twilio_creds = TwilioInformation()
callers = {
    twilio_creds.get_primary_phone(): "Arvind",
    twilio_creds.get_secondary_phone(): "Cootie Patootie"
}

message_response = {
    'STOP_TRADING': '\nYou typed Stop Trading',
    'OPTIONS': '\nPlease type either "ACCOUNT", "LAST", or "STOP TRADING"\n\nACCOUNT: typing this will get you information '
           'about your current account balance.\n\nLAST: typing this will execute your last successful command.'
           '\n\nSTOP_TRADING: typing this will cancel all unfilled orders and stop the trading algorithm'
}

logging.basicConfig(filename='sms_server.log',level=logging.INFO)

@app.route("/", methods=['GET', 'POST'])
def hello():
    global last_message
    global gdax_client
    global callers
    global message_response

    from_number = request.values.get('From', None)
    logging.info('{MESSAGE_RECEIVED_FROM: %s}', from_number)
    if from_number in callers:
        body = request.values.get('Body', None)
        logging.info('{MESSAGE_BODY: %s}', body)
        body = body.upper()
        resp = MessagingResponse()
        message = 'Unknown Command. Please type either "ACCOUNT" or "STOP TRADING". You can type "OPTIONS" for more information'
        if 'ACCOUNT' in body:
            last_message = 'ACCOUNT'
            message = gdax_client.get_account_details()
        elif 'STOP TRADING' in body:
            last_message = 'STOP_TRADING'
            message = message_response['STOP_TRADING']
        elif 'LAST' in body:
            if last_message == 'ACCOUNT':
                message = gdax_client.get_account_details()
            elif last_message in message_response:
                message = message_response[last_message]
        elif 'OPTIONS' in body:
            last_message = 'OPTIONS'
            message = message_response['OPTIONS']
        elif 'HI' in body or 'HELLO' in body:
            last_message = 'HI'
            message = 'Hello ' + callers[from_number]

        resp.message(message)
        return str(resp)

    return 'Go away. This is not for you!'

if __name__ == "__main__":
    app.run(debug=True)