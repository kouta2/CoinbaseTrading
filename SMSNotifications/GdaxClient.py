
import gdax
import logging

logging.basicConfig(filename='sms_server.log',level=logging.INFO)

class GdaxClient:
    def __init__(self):
        with open('../TradingAlgo/secrets.txt') as f:
            gdax_info = f.readlines()

        passphrase = (gdax_info[0].split(':'))[1].strip()
        key = (gdax_info[1].split(':'))[1].strip()
        secret = (gdax_info[2].split(':'))[1].strip()
        self.auth_client = gdax.AuthenticatedClient(key, secret.encode('ascii'), passphrase)


    def get_account_details(self):
        try:
            account_info = self.auth_client.get_accounts()
            msg = '\nAccount Info:\n\n'
            for account in account_info:
                msg += account['currency'] + ': ' + account['available'] + '\n'
            return msg[:-1]
        except BaseException as e:
            logging.info('{ERROR_GETTING_ACCOUNT_DETAILS: %s}', e)
            return '\nError Getting Account Details'
