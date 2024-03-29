from datetime import datetime, timedelta
from decimal import Decimal
import copy
import gdax
import json
import logging
import requests
import signal
import sys
import time

from TradingAlgo.Order import Order
from TradingAlgo.OrderBook import OrderBook
from TradingAlgo.PositionHandler import PositionHandler
from TradingAlgo.PriceHandler import PriceHandler

API_URL = 'https://api.gdax.com'
logging.basicConfig(filename='trade.log',level=logging.INFO)

class TradeAlgo:

    def __init__(self, key, secret, passphrase, product, num_days_of_historic_data):
        self.MINUTES_SPAN_OF_ONE_API_CALL = 450  # want 450 data points per API call
        self.GRANULARITY = 60  # want a data point every minute
        self.BUY_PERCENT = round(Decimal(.01), 2)
        self.SELL_PERCENT = round(Decimal(.01), 2)
        self.ORDER_SIZES = round(Decimal(.0005), 4) # round(Decimal(.0001), 4) # sizes of my buy and sell orders
        self.MAX_POSITION = round(Decimal(.1), 1) # my max position I can be
        self.MIN_POSITION = round(Decimal(0.0), 1) # my min position I can be

        self.product = product # the currency I am trading

        self.pending_orders = {} # maps order_ids to orders
        self.cancelled_orders = {} # maps order_ids to orders

        self.auth_client = TradeAlgo.connect_to_gdax(key, secret, passphrase) # client used to make API calls
        self.historic_data = self.get_last_x_minutes_of_data(15) # collect historic data first

        # Pass historic data into PriceHandler to get ranges of prices
        self.price_handler = PriceHandler(historic_data=self.historic_data)
        self.update_sell_and_buy_prices()

        time.sleep(1)
        self.position_handler = PositionHandler(product, self.get_account_details(product), self.auth_client.get_orders(product))

        self.order_book = OrderBook(product=product)  # Create a connection to the order book on the exchange
        logging.info('{ type: INIT, time: %s,  position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f, sell_price: %.2f, buy_price: %.2f }', datetime.utcnow(), float(self.position_handler.get_position()), float(self.position_handler.get_soft_position()), float(self.position_handler.get_cash()), float(self.position_handler.get_soft_cash()), float(self.sell_price), float(self.buy_price))

    def update_sell_and_buy_prices(self):
        median_price = self.price_handler.get_median_price()
        self.sell_price = round((1 + self.SELL_PERCENT) * median_price, 2)
        self.buy_price = round((1 - self.BUY_PERCENT) * median_price, 2)
        # avg_price = self.price_handler.get_avg_price()
        # self.sell_price = round((1 + self.SELL_PERCENT) * avg_price, 2)
        # self.buy_price = round((1 - self.BUY_PERCENT) * avg_price, 2)
        logging.info('{ type: UPDATE_SELL_AND_BUY_PRICES, time: %s, sell_price: %.2f, buy_price: %.2f }',
                     datetime.utcnow(), float(self.sell_price), float(self.buy_price))

    def get_account_details(self, product):
        accounts = self.auth_client.get_accounts()
        product_split = product.split('-')
        currency1 = product_split[0].strip()
        currency2 = product_split[1].strip()
        ret = []
        for account in accounts:
            if account['currency'] == currency1 or account['currency'] == currency2:
                ret.append(account)

        logging.info('{ type: GET_ACCOUNT_DETAILS, time: %s, account_info: %s}', datetime.utcnow(), ret)
        return ret

    @staticmethod
    def connect_to_gdax(key, secret, passphrase):
        return gdax.AuthenticatedClient(key, secret.encode('ascii'), passphrase)

    def get_last_hour_of_data(self):
        end_time = datetime.utcnow()
        minute_span = timedelta(hours=1)  # want a data point every minute
        start_time = end_time - minute_span
        logging.info('{ type: GET_LAST_HOUR_OF_HISTORIC_DATA, time: %s, start_time: %s, end_time: %s}',
                     datetime.utcnow(), start_time, end_time)
        return [list(reversed(self.auth_client.get_product_historic_rates(self.product, start=start_time,
                                                                        end=end_time)))]

    def get_last_x_minutes_of_data(self, x):
        curr_time = datetime.utcnow()
        logging.info('{ type: GET_LAST_X_MINUTES_OF_HISTORIC_DATA, time: %s}',
                     curr_time)
        start_time = curr_time - timedelta(minutes=x)
        end_time = min(curr_time, start_time + timedelta(minutes=200))
        historic_data = list(reversed(self.auth_client.get_product_historic_rates(self.product, start=start_time, end=end_time)))
        if x < 200:
            return [historic_data[-x:]]
        return [historic_data]

    def close_connections(self):
        logging.info('{ type: CLOSING_CONNECTION, time: %s}', datetime.utcnow())
        self.order_book.close_book()

    def update_status_of_unfilled_orders(self, i):
        try:
            recent_fills = self.auth_client.get_fills(product_id=self.product,limit=100)
            for page_of_fills in recent_fills:
                for fill in page_of_fills:
                    try:
                        if fill['order_id'] in self.pending_orders:
                            order = self.pending_orders[fill['order_id']]
                            if float(order.get_volume()) - float(fill['size']) < .00001:
                                order.set_is_completed(True)
                                self.position_handler.update_position(order)
                                logging.info('{ type: FILLED_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, side: %s, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f, order_complete: True}',
                                             datetime.utcnow(), fill['order_id'], float(fill['price']), float(fill['size']), fill['side'],
                                             float(round(self.position_handler.get_position(), 4)), float(round(self.position_handler.get_soft_position(), 4)),
                                             float(round(self.position_handler.get_cash(), 2)), float(round(self.position_handler.get_soft_cash(), 2)))
                                del self.pending_orders[fill['order_id']]
                            else:
                                order.set_volume(order.get_volume() - float(fill['size']))
                                self.position_handler.update_position(
                                    Order(price=float(fill['price']), id=fill['order_id'], volume=float(fill['size']), side=fill['side'], is_completed=True))
                                logging.info(
                                    '{ type: FILLED_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, side: %s, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f, order_complete: False}',
                                    datetime.utcnow(), fill['order_id'], float(fill['price']), float(fill['size']),
                                    fill['side'],
                                    float(round(self.position_handler.get_position(), 4)),
                                    float(round(self.position_handler.get_soft_position(), 4)),
                                    float(round(self.position_handler.get_cash(), 2)),
                                    float(round(self.position_handler.get_soft_cash(), 2)))
                    except BaseException as e:
                        logging.info("{ERROR_PARSING_FILLS: %s, recent_fills: %s}", e, fill)

            if i == 0:
                # undo soft position and soft cash changes
                for order_id, order in self.cancelled_orders.items():
                    old_side = order.get_side()
                    if order.get_side() == 'buy':
                        order.set_side('sell')
                    else:
                        order.set_side('buy')
                    self.position_handler.restore_soft_info(order)
                    logging.info('{ type: CANCELLED_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, side: %s, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f}',
                                 datetime.utcnow(), order_id, float(order.get_price()), float(order.get_volume()), old_side,
                                 float(round(self.position_handler.get_position(), 4)), float(round(self.position_handler.get_soft_position(), 4)),
                                 float(round(self.position_handler.get_cash(), 2)), float(round(self.position_handler.get_soft_cash(), 2)))

                    if order_id in self.pending_orders: # if order_id is in pending, remove it cuz its been enough time
                        del self.pending_orders[order_id]

                # the cancelled orders for next time are the pending orders that weren't filled
                self.cancelled_orders = copy.deepcopy(self.pending_orders)
        except BaseException as e:
            logging.info("{ERROR_GETTING_FILLS: %s}", e)

    def can_buy(self, price):
        max_pos = max(self.position_handler.get_position(), self.position_handler.get_soft_position())
        min_cash = min(self.position_handler.get_cash(), self.position_handler.get_soft_cash())
        return max_pos + self.ORDER_SIZES < self.MAX_POSITION and min_cash >= price * self.ORDER_SIZES

    def place_buy_order(self, book_price):
        price = min(self.buy_price, book_price - round(Decimal(.02), 2))
        if self.buy_price - price > Decimal(.02):
            self.buy_price = price - round(Decimal(.05), 2)
        if self.can_buy(price) == True:
            order_url = API_URL + '/orders'
            order_data = {
                'type': 'limit',
                'side': 'buy',
                'product_id': self.product,
                'price': float(price),
                'size': float(self.ORDER_SIZES),
                'time_in_force': 'GTT',
                'cancel_after': 'min',
                'post_only': True
            }
            response = ''
            try:
                response = requests.post(order_url, data=json.dumps(order_data), auth=self.auth_client.auth)
                # print(response.json())
                if response.status_code == 200:
                    json_response = json.loads(response.text)
                    new_order = Order(price, self.ORDER_SIZES, json_response['id'], 'buy', False)
                    self.position_handler.update_position(new_order)
                    self.pending_orders[json_response['id']] = new_order
                    logging.info('{ type: BUY_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f}',
                                 datetime.utcnow(), json_response['id'], float(price), float(self.ORDER_SIZES),
                                float(round(self.position_handler.get_position(), 4)), float(round(self.position_handler.get_soft_position(), 4)),
                                float(round(self.position_handler.get_cash(), 2)), float(round(self.position_handler.get_soft_cash(), 2)))
                else:
                    logging.info('{ type: BAD_BUY_ORDER_REQUEST, time: %s, response: %s}', datetime.utcnow(), response.json())
            except BaseException as e:
                logging.info("{ERROR_MAKING_BUY_ORDER: %s, time: %s, response: %s}", e, datetime.utcnow(), response)

    def can_sell(self):
        min_pos = min(self.position_handler.get_position(), self.position_handler.get_soft_position())
        return min_pos - self.ORDER_SIZES > self.MIN_POSITION

    def place_sell_order(self, book_price):
        price = max(self.sell_price, book_price + round(Decimal(.02), 2))
        if price - self.sell_price > Decimal(.02):
            self.sell_price = price + round(Decimal(.05), 2)
        if self.can_sell() == True:
            order_url = API_URL + '/orders'
            order_data = {
                'type': 'limit',
                'side': 'sell',
                'product_id': self.product,
                'price': float(price),
                'size': float(self.ORDER_SIZES),
                'time_in_force': 'GTT',
                'cancel_after': 'min',
                'post_only': True
            }
            response = ''
            try:
                response = requests.post(order_url, data=json.dumps(order_data), auth=self.auth_client.auth)
                # print(response.json())
                if response.status_code == 200:
                    json_response = json.loads(response.text)
                    new_order = Order(price, self.ORDER_SIZES, json_response['id'], 'sell', False)
                    self.position_handler.update_position(new_order)
                    self.pending_orders[json_response['id']] = new_order
                    logging.info(
                        '{ type: SELL_ORDER, time: %s, order_id: %s, price: %.2f, size: %.4f, position: %.4f, soft_position: %.4f, cash: %.2f, soft_cash: %.2f}',
                        datetime.utcnow(), json_response['id'], float(price), float(self.ORDER_SIZES),
                        float(round(self.position_handler.get_position(), 4)), float(round(self.position_handler.get_soft_position(), 4)),
                        float(round(self.position_handler.get_cash(), 2)), float(round(self.position_handler.get_soft_cash(), 2)))
                else:
                    logging.info('{ type: BAD_SELL_ORDER_REQUEST, time: %s, response: %s}', datetime.utcnow(), response.json())
            except BaseException as e:
                logging.info("{ERROR_MAKING_SELL_ORDER: %s, time: %s, response: %s}", e, datetime.utcnow(), response)

    def execute(self):
        while True:
            i = 0
            new_prices = []
            while i < 15:
                self.update_status_of_unfilled_orders(i)  # update position
                curr_asks = self.order_book.get_sell_orders()
                curr_bids = self.order_book.get_buy_orders()
                if i == 0:
                    if len(curr_asks) > 0:
                        self.place_buy_order(curr_asks[0].get_price())
                    if len(curr_bids) > 0:
                        self.place_sell_order(curr_bids[0].get_price())
                else:
                    if len(curr_asks) > 0 and curr_asks[0].get_price() <= self.buy_price:
                        self.place_buy_order(curr_asks[0].get_price())

                    if len(curr_bids) > 0 and curr_bids[0].get_price() >= self.sell_price:
                        self.place_sell_order(curr_bids[0].get_price())

                    if len(curr_asks) > 0 and len(curr_bids) > 0:
                        new_prices.append((curr_asks[0].get_price() + curr_bids[0].get_price()) / 2)

                time.sleep(4) # need to sleep for a second between API calls
                try:
                    self.order_book.update_book()
                except BaseException as e:
                    logging.info('{ERROR_UPDATING_BOOK: %s}', e)
                # print('ASKS:\n' + str([o.get_price() for o in self.order_book.get_sell_orders()]))
                # print('BIDS:\n' + str([o.get_price() for o in self.order_book.get_buy_orders()]) + '\n')
                i += 1
            self.price_handler.update_price_info(datetime.utcnow(), new_prices)
            self.update_sell_and_buy_prices()
            time.sleep(1)

if __name__=="__main__":
    logging.info('{STARTED: true}')
    def signal_handler(signal, frame):
        logging.info('{ type: SIGINT_RECEIVED, time: %s}', datetime.utcnow())
        try:
            trade_algo.close_connections()
        except:
            logging.info('{ type: OBJECT_NOT_INSTANTIATED, time: %s}', datetime.utcnow())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    token_info = []
    with open('secrets.txt') as f:
        token_info = f.readlines()

    API_PASS = (token_info[0].split(':'))[1].strip()
    API_KEY = (token_info[1].split(':'))[1].strip()
    API_SECRET = (token_info[2].split(':'))[1].strip()
    product_id = 'BTC-USD'
    num_days_of_historic_data = 2

    while True:
        try:
            trade_algo = TradeAlgo(API_KEY, API_SECRET, API_PASS, product_id, num_days_of_historic_data)
            trade_algo.execute()
            trade_algo.close_connections()
        except BaseException as e:
            logging.info('{ type: ERROR_IN_MAIN, time: %s, error: %s}', datetime.utcnow(), e)



