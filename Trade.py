from datetime import datetime, timedelta
import copy
import gdax
import json
import logging
import requests
import signal
import sys
import time

from Order import Order
from OrderBook import OrderBook
from PositionHandler import PositionHandler
from PriceHandler import PriceHandler

API_URL = 'https://api.gdax.com'
logging.basicConfig(filename='trade.log',level=logging.INFO)


class TradeAlgo:

    def __init__(self, key, secret, passphrase, product, num_days_of_historic_data):
        self.MINUTES_SPAN_OF_ONE_API_CALL = 450  # want 450 data points per API call
        self.GRANULARITY = 60  # want a data point every minute
        self.PERCENT = .03 # percent up and down from the median/average I want to buy and sell
        self.ORDER_SIZES = .0001 # sizes of my buy and sell orders
        self.MAX_POSITION = .1 # my max position I can be
        self.MIN_POSITION = 0.0 # my min position I can be

        self.product = product # the currency I am trading

        self.pending_orders = {} # maps order_ids to orders
        self.cancelled_orders = {} # maps order_ids to orders

        self.auth_client = TradeAlgo.connect_to_gdax(key, secret, passphrase) # client used to make API calls
        self.historic_data = self.get_historic_data(num_days_of_historic_data) # collect historic data first

        # Pass historic data into PriceHandler to get ranges of prices
        self.price_handler = PriceHandler(historic_data=self.historic_data)
        self.update_sell_and_buy_prices()

        time.sleep(1)
        self.position_handler = PositionHandler(product, self.get_account_details(product), self.auth_client.get_orders(product))

        self.order_book = OrderBook(product=product)  # Create a connection to the order book on the exchange
        logging.info('{ type: INIT, time: %s,  position: %.4f, cash: %.2f, sell_price: %.2f, buy_price: %.2f }',
                     datetime.now(), self.position_handler.get_position(), self.position_handler.get_cash(),
                     self.sell_price, self.buy_price)

    def update_sell_and_buy_prices(self):
        # median_price = self.price_handler.get_median_price()
        # self.sell_price = round((1 + self.PERCENT) * median_price, 2)
        # self.buy_price = round((1 - self.PERCENT) * median_price, 2)
        avg_price = self.price_handler.get_avg_price()
        self.sell_price = round((1 + self.PERCENT) * avg_price, 2)
        self.buy_price = round((1 - self.PERCENT) * avg_price, 2)
        logging.info('{ type: UPDATE_SELL_AND_BUY_PRICES, time: %s, sell_price: %.2f, buy_price: %.2f }',
                     datetime.now(), self.sell_price, self.buy_price)

    def get_account_details(self, product):
        accounts = self.auth_client.get_accounts()
        product_split = product.split('-')
        currency1 = product_split[0].strip()
        currency2 = product_split[1].strip()
        ret = []
        for account in accounts:
            if account['currency'] == currency1 or account['currency'] == currency2:
                ret.append(account)

        logging.info('{ type: GET_ACCOUNT_DETAILS, time: %s, account_info: %s}', datetime.now(), ret)
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
        logging.info('{ type: GET_LAST_MIN_OF_HISTORIC_DATA, time: %s, start_time: %s, end_time: %s}',
                     datetime.now(), start_time, end_time)
        return self.auth_client.get_product_historic_rates(self.product, start=start_time,
                                                                        end=end_time)

    def close_connections(self):
        logging.info('{ type: CLOSING_CONNECTION, time: %s}', datetime.now())
        self.order_book.close_book()

    def update_status_of_unfilled_orders(self, i):
        recent_fills = self.auth_client.get_fills(product_id=self.product)
        for page_of_fills in recent_fills:
            for fill in page_of_fills:
                if fill['order_id'] in self.pending_orders:
                    order = self.pending_orders[fill['order_id']]
                    order.set_is_completed(True)
                    self.position_handler.update_position(order)
                    logging.info('{ type: FILLED_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, side: %s, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f}',
                                 datetime.now(), fill['order_id'], fill['price'], fill['size'], fill['side'],
                                 self.position_handler.get_position(), self.position_handler.get_soft_position(),
                                 self.position_handler.get_cash(), self.position_handler.get_soft_cash())
                    del self.pending_orders[fill['order_id']]

        if i == 0:
            # undo soft position and soft cash changes
            for order_id, order in self.cancelled_orders.items():
                logging.info('{ type: CANCELLED_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, side: %s}',
                             datetime.now(), order_id, order.get_price(), order.get_volume(), order.get_side())
                if order.get_side() == 'buy':
                    order.set_side('sell')
                else:
                    order.set_side('buy')
                self.position_handler.update_position(order)

                if order_id in self.pending_orders: # if order_id is in pending, remove it cuz its been enough time
                    del self.pending_orders[order_id]

            # the cancelled orders for next time are the pending orders that weren't filled
            self.cancelled_orders = copy.deepcopy(self.pending_orders)

    def can_buy(self):
        max_pos = max(self.position_handler.get_position(), self.position_handler.get_soft_position())
        min_cash = min(self.position_handler.get_cash(), self.position_handler.get_soft_cash())
        return max_pos + self.ORDER_SIZES < self.MAX_POSITION and \
               min_cash >= self.buy_price * self.ORDER_SIZES

    def place_buy_order(self):
        if self.can_buy():
            order_url = API_URL + '/orders'
            order_data = {
                'type': 'limit',
                'side': 'buy',
                'product_id': self.product,
                'price': self.buy_price,
                'size': self.ORDER_SIZES,
                'time_in_force': 'GTT',
                'cancel_after': 'min',
                'post_only': True
            }
            response = requests.post(order_url, data=json.dumps(order_data), auth=self.auth_client.auth)
            print(response.json())
            if response.status_code == 200:
                json_response = json.loads(response.text)
                new_order = Order(self.buy_price, self.ORDER_SIZES, json_response['id'], 'buy', False)
                self.position_handler.update_position(new_order)
                self.pending_orders[json_response['id']] = new_order
                logging.info('{ type: BUY_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f}',
                             datetime.now(), json_response['id'], self.buy_price, self.ORDER_SIZES,
                    self.position_handler.get_position(), self.position_handler.get_soft_position(),
                    self.position_handler.get_cash(), self.position_handler.get_soft_cash())
            else:
                logging.info('{ type: BUY_ORDER, time: %s, error: True, response: %s}', datetime.now(), response.json())

    def can_sell(self):
        min_pos = min(self.position_handler.get_position(), self.position_handler.get_soft_position())
        return min_pos - self.ORDER_SIZES > self.MIN_POSITION

    def place_sell_order(self):
        if self.can_sell():
            order_url = API_URL + '/orders'
            order_data = {
                'type': 'limit',
                'side': 'sell',
                'product_id': self.product,
                'price': self.sell_price,
                'size': self.ORDER_SIZES,
                'time_in_force': 'GTT',
                'cancel_after': 'min',
                'post_only': True
            }
            response = requests.post(order_url, data=json.dumps(order_data), auth=self.auth_client.auth)
            print(response.json())
            if response.status_code == 200:
                json_response = json.loads(response.text)
                new_order = Order(self.sell_price, self.ORDER_SIZES, json_response['id'], 'sell', False)
                self.position_handler.update_position(new_order)
                self.pending_orders[json_response['id']] = new_order
                logging.info(
                    '{ type: SELL_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f}',
                    datetime.now(), json_response['id'], self.sell_price, self.ORDER_SIZES,
                    self.position_handler.get_position(), self.position_handler.get_soft_position(),
                    self.position_handler.get_cash(), self.position_handler.get_soft_cash())
            else:
                logging.info('{ type: SELL_ORDER, time: %s, error: True, response: %s}', datetime.now(), response.json())

    def execute(self):
        while True:
            i = 0
            new_prices = []
            while i < 15:
                self.update_status_of_unfilled_orders(i)  # update position
                if i == 0:
                    self.place_buy_order()
                    self.place_sell_order()
                else:
                    curr_asks = self.order_book.get_asks()
                    if len(curr_asks) > 0 and curr_asks[0].get_price() <= self.buy_price:
                        self.place_buy_order()

                    curr_bids = self.order_book.get_bids()
                    if len(curr_bids) > 0 and curr_bids[0].get_price() >= self.sell_price:
                        self.place_sell_order()

                    if len(curr_asks) > 0 and len(curr_bids) > 0:
                        new_prices.append((curr_asks[0].get_price() + curr_bids[0].get_price()) / 2)

                time.sleep(4) # need to sleep for a second between API calls
                self.order_book.update_book()
                i += 1
            self.price_handler.update_price_info(datetime.now(), new_prices)
            self.update_sell_and_buy_prices()
            time.sleep(1)

if __name__=="__main__":
    logging.info('{STARTED: true}')
    def signal_handler(signal, frame):
        logging.info('{ type: SIGINT_RECEIVED, time: %s}', datetime.now())
        try:
            trade_algo.close_connections()
        except:
            logging.info('{ type: OBJECT_NOT_INSTANTIATED, time: %s}', datetime.now())
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



