from datetime import datetime, timedelta
import gdax
import json
import requests
import signal
import sys
import time

from Order import Order
from OrderBook import OrderBook
from PositionHandler import PositionHandler
from PriceHandler import PriceHandler

API_URL = 'https://api.gdax.com'

class TradeAlgo:

    def __init__(self, key, secret, passphrase, product, num_days_of_historic_data):
        self.MINUTES_SPAN_OF_ONE_API_CALL = 450  # want 450 data points per API call
        self.GRANULARITY = 60  # want a data point every minute
        self.PERCENT = .03 # percent up and down from the median/average I want to buy and sell
        self.ORDER_SIZES = '.001'
        self.MAX_POSITION = .1
        self.MIN_POSITIION = 0.0

        self.product = product

        self.auth_client = TradeAlgo.connect_to_gdax(key, secret, passphrase) # client used to make API calls
        self.historic_data = self.get_historic_data(num_days_of_historic_data) # collect historic data first

        # Pass historic data into PriceHandler to get ranges of prices
        self.price_handler = PriceHandler(historic_data=self.historic_data)

        time.sleep(1)
        self.position_handler = PositionHandler(product, self.get_account_details(product), self.auth_client.get_orders(product))

        self.order_book = OrderBook(product=product)  # Create a connection to the order book on the exchange

    def update_sell_and_buy_prices(self):
        median_price = self.price_handler.get_median_price()
        self.sell_price = (1 + self.PERCENT) * median_price
        self.buy_price = (1 - self.PERCENT) * median_price

    def get_account_details(self, product):
        accounts = self.auth_client.get_accounts()
        product_split = product.split('-')
        currency1 = product_split[0].strip()
        currency2 = product_split[1].strip()
        ret = []
        for account in accounts:
            if account['currency'] == currency1 or account['currency'] == currency2:
                ret.append(account)

        return ret

    @staticmethod
    def connect_to_gdax(key, secret, passphrase):
        return gdax.AuthenticatedClient(key, secret.encode('ascii'), passphrase)

    '''
        returns a list of list of historic data for the past num_days_of_historic_data every minute
    '''
    def get_historic_data(self, num_days_of_historic_data):
        curr_time = datetime.now()
        delta_from_current_time = timedelta(days=num_days_of_historic_data)
        minute_span = timedelta(minutes=self.MINUTES_SPAN_OF_ONE_API_CALL) # want a data point every minute
        start_time = curr_time - delta_from_current_time
        historic_data = []
        num_api_calls = 0
        while (start_time + minute_span) <= curr_time:
            history_chunk = self.auth_client.get_product_historic_rates(self.product, start=start_time, granularity=self.GRANULARITY)
            historic_data.append(history_chunk[::-1])
            start_time += minute_span
            num_api_calls += 1
            if num_api_calls == 3:
                time.sleep(1)
                print('need to sleep to not exceed rate limit')
                num_api_calls = 0

        return historic_data

    def get_last_minute_of_data(self):
        end_time = datetime.now()
        minute_span = timedelta(minutes=1)  # want a data point every minute
        start_time = end_time - minute_span
        return self.auth_client.get_product_historic_rates(self.product, start=start_time,
                                                                        end=end_time)

    def close_connections(self):
        self.order_book.close_book()

    def execute(self):
        while True:
            i = 0
            while i < 15:
                if i == 0:
                    self.place_buy_order()
                    self.place_sell_order()
                else:
                    curr_asks = self.order_book.get_asks()
                    if curr_asks[0].get_price() <= self.buy_price:
                        self.place_buy_order()

                    curr_bids = self.order_book.get_bids()
                    if curr_bids[0].get_price() >= self.sell_price:
                        self.place_sell_order()

                self.check_for_filled_orders() # update position here
                time.sleep(4) # need to sleep for a second between API calls
                self.order_book.update_book()
                i += 1
            self.cancel_orders()
            self.price_handler.update_price_info(self.get_last_minute_of_data())
            self.update_sell_and_buy_prices()


    def place_buy_order(self):
        if self.position_handler.get_position() < self.MAX_POSITION:
            order_url = API_URL + '/orders'
            order_data = {
                'type': 'limit',
                'side': 'buy',
                'product_id': self.product,
                'price': self.buy_price,
                'size': self.ORDER_SIZES,
                'time_in_force': 'GTT',
                'cancel_after': '1 min',
                'post_only': True
            }
            response = requests.post(order_url, data=json.dumps(order_data), auth=self.auth_client.auth)
            print(response.json())
            if response.status_code == 200:
                json_response = json.loads(response.text)
                self.position_handler.update_position(Order(self.buy_price, self.ORDER_SIZES, json_response['id'], 'buy', False))
            # self.auth_client.buy(price=str(self.buy_price), size=self.ORDER_SIZES, product_id=self.product)

    def place_sell_order(self):
        if self.position_handler.get_position() > self.MIN_POSITIION:
            order_url = API_URL + '/orders'
            order_data = {
                'type': 'limit',
                'side': 'sell',
                'product_id': self.product,
                'price': self.sell_price,
                'size': self.ORDER_SIZES,
                'time_in_force': 'GTT',
                'cancel_after': '1 min',
                'post_only': True
            }
            response = requests.post(order_url, data=json.dumps(order_data), auth=self.auth_client.auth)
            print(response.json())
            if response.status_code == 200:
                json_response = json.loads(response.text)
                self.position_handler.update_position(
                    Order(self.sell_price, self.ORDER_SIZES, json_response['id'], 'sell', False))

            # self.auth_client.sell(price=str(self.sell_price), size=self.ORDER_SIZES, product_id=self.product)

if __name__=="__main__":
    def signal_handler(signal, frame):
        print('Cleanup...')
        try:
            trade_algo.close_connections()
        except:
            print('You have not created a TradeAlgo object yet')
        print('Successful Cleanup!')
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    token_info = []
    with open('secrets.txt') as f:
        token_info = f.readlines()

    API_PASS = (token_info[0].split(':'))[1].strip()
    API_KEY = (token_info[1].split(':'))[1].strip()
    API_SECRET = (token_info[2].split(':'))[1].strip()
    product_id = 'BCH-USD'
    num_days_of_historic_data = 2

    trade_algo = TradeAlgo(API_KEY, API_SECRET, API_PASS, product_id, num_days_of_historic_data)

    trade_algo.execute()

    trade_algo.close_connections()



