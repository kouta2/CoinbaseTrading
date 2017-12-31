
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
        account_details = self.get_account_available()
        if account_details != 'Error Getting Account Details':
            pending_orders = self.get_pending_orders()
            if pending_orders != '':
                for page_of_orders in pending_orders:
                    for order in page_of_orders:
                        product_id = order['product_id'].split('-')
                        size = float(order['size'])
                        if order['side'] == 'buy':
                            currency = product_id[1]
                            price = float(order['price'])
                            account_details[currency] += size * price
                        else:
                            currency = product_id[0]
                            account_details[currency] += size
                            account_details[currency] = round(account_details[currency], 4)
            account_string = ''
            for key, val in account_details.items():
                account_string += key + ': ' + str(val) + '\n'
            return '\nAccount Info:\n\n' + account_string[:-1]
        else:
            return '\nAccount Info:\n\n' + account_details

    def get_account_available(self):
        try:
            account_info = self.auth_client.get_accounts()
            account_dict = {}
            for account in account_info:
                account_dict[account['currency']] = float(account['available'])
            return account_dict
        except BaseException as e:
            logging.info('{ERROR_GETTING_ACCOUNT_DETAILS: %s}', e)
            return 'Error Getting Account Details'

    def get_pending_orders(self):
        try:
            return self.auth_client.get_orders()
        except BaseException as e:
            logging.info('{ERROR_GETTING_PENDING_ORDERS: %s}', e)
            return ''
