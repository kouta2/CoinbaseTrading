from datetime import datetime, timedelta
import gdax
import signal
import sys
import time

from OrderBook import OrderBook
from PriceHandler import PriceHandler

class TradeAlgo:

    def __init__(self, key, secret, passphrase, product, num_days_of_historic_data):
        self.MINUTES_SPAN_OF_ONE_API_CALL = 450  # want 450 data points per API call
        self.GRANULARITY = 60  # want a data point every minute
        self.PERCENT = .05 # percent up and down from the median/average I want to buy and sell

        self.auth_client = TradeAlgo.connect_to_gdax(key, secret, passphrase) # client used to make API calls
        self.historic_data = self.get_historic_data(num_days_of_historic_data) # collect historic data first

        # Pass historic data into PriceHandler to get ranges of prices
        self.price_handler = PriceHandler(historic_data=self.historic_data)
        median_price = self.price_handler.get_median_price()
        self.sell_price = (1 + self.PERCENT) * median_price
        self.buy_price = (1 - self.PERCENT) * median_price

        self.order_book = OrderBook(product=product) # Create a connection to the order book on the exchange

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
        while (start_time + minute_span) < curr_time:
            history_chunk = self.auth_client.get_product_historic_rates('ETH-USD', start=start_time, granularity=self.GRANULARITY)
            historic_data.append(history_chunk[::-1])
            start_time += minute_span
            num_api_calls += 1
            if num_api_calls == 3:
                time.sleep(1)
                print('need to sleep to not exceed rate limit')
                num_api_calls = 0

        return historic_data

    def close_connections(self):
        self.order_book.close_book()

    def execute(self):
        pass

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

    API_PASS = (token_info[0].split(':'))[1]
    API_KEY = (token_info[1].split(':'))[1]
    API_SECRET = (token_info[2].split(':'))[1]
    product_id = 'BCH-USD'
    num_days_of_historic_data = 2

    trade_algo = TradeAlgo(API_KEY, API_SECRET, API_PASS, product_id, num_days_of_historic_data)

    trade_algo.execute()

    trade_algo.close_connections()
