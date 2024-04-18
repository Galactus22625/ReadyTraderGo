# Copyright 2021 Optiver Asia Pacific Pty. Ltd.
#
# This file is part of Ready Trader Go.
#
#     Ready Trader Go is free software: you can redistribute it and/or
#     modify it under the terms of the GNU Affero General Public License
#     as published by the Free Software Foundation, either version 3 of
#     the License, or (at your option) any later version.
#
#     Ready Trader Go is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public
#     License along with Ready Trader Go.  If not, see
#     <https://www.gnu.org/licenses/>.
import asyncio
import itertools
import math
import time
import asyncio
import numpy as np

from typing import List

from ready_trader_go import BaseAutoTrader, Instrument, Lifespan, MAXIMUM_ASK, MINIMUM_BID, Side


LOT_SIZE = 10
POSITION_LIMIT = 100
TICK_SIZE_IN_CENTS = 100
MIN_BID_NEAREST_TICK = (MINIMUM_BID + TICK_SIZE_IN_CENTS) // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS
MAX_ASK_NEAREST_TICK = MAXIMUM_ASK // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS

DISTRIBUTION_MEMORY = 1000
#it seems for arbitrage rolling is too slow
#increments of 10, rolling mean distributin for arbitrage
#does not close stances


class AutoTrader(BaseAutoTrader):
    """Example Auto-trader.

    When it starts this auto-trader places ten-lot bid and ask orders at the
    current best-bid and best-ask prices respectively. Thereafter, if it has
    a long position (it has bought more lots than it has sold) it reduces its
    bid and ask prices. Conversely, if it has a short position (it has sold
    more lots than it has bought) then it increases its bid and ask prices.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, team_name: str, secret: str):
        """Initialise a new instance of the AutoTrader class."""
        super().__init__(loop, team_name, secret)
        self.order_ids = itertools.count(1)
        self.bids = set()
        self.asks = set()
        self.ask_id = self.ask_price = self.bid_id = self.bid_price = self.position = 0
        self.etfprice = 0           #last caluclated etf price
        self.futureprice = 0        #last calculated future price
        self.differencemean = 0     #mean of etf - future
        self.differencevariance = 0  #faster calculations? idk variance diff
        self.differencestdeviation = 0  #std deviation of etf - future
        self.numdatapoints = 0      #number of points included in dataset
        self.differencetracker = np.zeros(DISTRIBUTION_MEMORY)        #in case we want to only use x recent data points for normal model instead of all data ever
                                            #we record x points of etf-future, then when we are above x, we replace one value, remove that value
                                            #  from mean and stdeviation, and replace with new value (math)

        #store most recent prices
        self.futureaskprice = 0
        self.futurebidprice = 0
        self.etfaskprice = 0
        self.etfbidprice = 0

        self.activevolume = 0


        #prevent putting too many orders in, and then having them all filled at once to go voer hold limit
        self.activebuy = 0
        self.activesell = 0   

        #we create an event loop to ensure our hedges are performing in the proper order
        #self.hedgechecker = asyncio.new_event_loop()
        self.hedgeneeded = 0

    def on_error_message(self, client_order_id: int, error_message: bytes) -> None:
        """Called when the exchange detects an error.

        If the error pertains to a particular order, then the client_order_id
        will identify that order, otherwise the client_order_id will be zero.
        """
        self.logger.warning("error with order %d: %s", client_order_id, error_message.decode())
        if client_order_id != 0 and (client_order_id in self.bids or client_order_id in self.asks):
            self.on_order_status_message(client_order_id, 0, 0, 0)

    def on_hedge_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
        """Called when one of your hedge orders is filled.

        The price is the average price at which the order was (partially) filled,
        which may be better than the order's limit price. The volume is
        the number of lots filled at that price.
        """
        self.logger.info("received hedge filled for order %d with average price %d and volume %d", client_order_id,
                         price, volume)
        
        # #if clined order id in which
        # if client_order_id in self.bids:
        #     self.hedgeposition -= volume
        # else:
        #     self.hedgeposition += volume

        # if self.hedgeneeded > 0:
        #     self.send_hedge_order(next(self.order_ids), Side.ASK, MIN_BID_NEAREST_TICK, self.hedgeneeded)
        # elif self.hedgeneeded < 0:
        #     self.send_hedge_order(next(self.order_ids), Side.BID, MAX_ASK_NEAREST_TICK, self.hedgediff)




    def on_order_book_update_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                                     ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        """Called periodically to report the status of an order book.

        The sequence number can be used to detect missed or out-of-order
        messages. The five best available ask (i.e. sell) and bid (i.e. buy)
        prices are reported along with the volume available at each of those
        price levels.
        """
       #self.logger.info("received order book for instrument %d with sequence number %d", instrument,
        #                 sequence_number)
        #we can use this to access most recent prices
        if instrument == Instrument.FUTURE:
            self.futureaskprice = ask_prices[0]
            self.futurebidprice = bid_prices[0]
        else:
            self.etfaskprice = ask_prices[0]
            self.etfbidprice = bid_prices[0]

        if len(self.bids)>9:
            self.send_cancel_order(min(self.bids))
        if len(self.asks) >9:
            self.send_cancel_order(min(self.asks))

        
        #original trader balance trading?
        # if instrument == Instrument.FUTURE:
        #     price_adjustment = - (self.position // LOT_SIZE) * TICK_SIZE_IN_CENTS
        #     new_bid_price = bid_prices[0] + price_adjustment if bid_prices[0] != 0 else 0
        #     new_ask_price = ask_prices[0] + price_adjustment if ask_prices[0] != 0 else 0

        #     if self.bid_id != 0 and new_bid_price not in (self.bid_price, 0):
        #         self.send_cancel_order(self.bid_id)
        #         self.bid_id = 0
        #     if self.ask_id != 0 and new_ask_price not in (self.ask_price, 0):
        #         self.send_cancel_order(self.ask_id)
        #         self.ask_id = 0

        #     if self.bid_id == 0 and new_bid_price != 0 and self.position < POSITION_LIMIT:
        #         self.bid_id = next(self.order_ids)
        #         self.bid_price = new_bid_price
        #         self.send_insert_order(self.bid_id, Side.BUY, new_bid_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
        #         self.bids.add(self.bid_id)

        #     if self.ask_id == 0 and new_ask_price != 0 and self.position > -POSITION_LIMIT:
        #         self.ask_id = next(self.order_ids)
        #         self.ask_price = new_ask_price
        #         self.send_insert_order(self.ask_id, Side.SELL, new_ask_price, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
        #         self.asks.add(self.ask_id)

    def on_order_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
        """Called when one of your orders is filled, partially or fully.

        The price is the price at which the order was (partially) filled,
        which may be better than the order's limit price. The volume is
        the number of lots filled at that price.
        """
        self.logger.info("received order filled for order %d with price %d and volume %d", client_order_id,
                         price, volume)

        #original hedge
        if client_order_id in self.bids:
            self.position += volume
            self.activebuy -= volume
            self.activevolume -= volume
            self.send_hedge_order(next(self.order_ids), Side.ASK, MIN_BID_NEAREST_TICK, volume)
            self.hedgeneeded += volume
            
            #self.bids.discard(client_order_id)       #remove bid from bid numbers sinc filled
        elif client_order_id in self.asks:
            self.position -= volume
            self.activesell -= volume
            self.activevolume -= volume
            self.send_hedge_order(next(self.order_ids), Side.BID, MAX_ASK_NEAREST_TICK, volume)
            self.hedgeneeded-= volume
            #self.asks.discard(client_order_id)           #remove ask from ask numbers since filled

        #simple position limiter, only works for increments of 10, need to check what orders are left in teh queue and remove just enough
        if self.position >= POSITION_LIMIT-11:
            for ask in self.bids:
                self.send_cancel_order(ask)
        elif self.position <= -POSITION_LIMIT+11:
            for bids in self.bids:
                self.send_cancel_order(bids) 

        #remove old orders
        if client_order_id in self.bids:
            for bid in self.bids:
                if bid < client_order_id - 25:
                    self.send_cancel_order(bid)
        elif client_order_id in self.asks:
            for ask in self.asks:
                if ask < client_order_id -25:
                    self.send_cancel_order(ask)

        
        # self.hedgechecker.call_soon(
        #     functools.partial(
        #     if self.position != -self.hedgeposition:

            
        # )
    


        #self.event_loop.time()      #track after something happens, to call back something, use for hedge insurance?

    def on_order_status_message(self, client_order_id: int, fill_volume: int, remaining_volume: int,
                                fees: int) -> None:
        """Called when the status of one of your orders changes.

        The fill_volume is the number of lots already traded, remaining_volume
        is the number of lots yet to be traded and fees is the total fees for
        this order. Remember that you pay fees for being a market taker, but
        you receive fees for being a market maker, so fees can be negative.

        If an order is cancelled its remaining volume will be zero.
        """
        self.logger.info("received order status for order %d with fill volume %d remaining %d and fees %d",
                         client_order_id, fill_volume, remaining_volume, fees)
        if remaining_volume == 0:
            if client_order_id == self.bid_id:
                self.bid_id = 0
            elif client_order_id == self.ask_id:
                self.ask_id = 0
            # It could be either a bid or an ask
            self.bids.discard(client_order_id)
            self.asks.discard(client_order_id)



    def on_trade_ticks_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                               ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        """Called periodically when there is trading activity on the market.

        The five best ask (i.e. sell) and bid (i.e. buy) prices at which there
        has been trading activity are reported along with the aggregated volume
        traded at each of those price levels.

        If there are less than five prices on a side, then zeros will appear at
        the end of both the prices and volumes arrays.
        """

        #instrument 0 is future, instrument 1 is etf (probably)
        self.logger.info("received trade ticks for instrument %d with sequence number %d", instrument,
                         sequence_number)
        #self.logger.info("ask price, ask volume, bid price, bid volume %d, %d, %d, %d", ask_prices[0], ask_volumes[0], bid_prices[0], bid_volumes[0])
        if instrument == Instrument.FUTURE:
            self.futureprice = max(ask_prices[0], bid_prices[0])        #since one is 0, we are finding the value of the one being used, future price is simply last traded price
        else:
            self.etfprice = max(ask_prices[0], bid_prices[0])                                      #assume etf is also last traded price (formula not relevant?)
        if self.etfprice != 0 and self.futureprice != 0:   #initial values are 0, so mess up starting point
            difference = self.etfprice - self.futureprice
            #increment number of datapoints
            self.numdatapoints += 1
            if self.numdatapoints<DISTRIBUTION_MEMORY:
                #find new mean
                self.differencemean = (self.differencemean * (self.numdatapoints - 1) + difference) / self.numdatapoints
                #find new variance
                self.differencevariance = (self.differencevariance * (self.numdatapoints - 1) + difference**2) / self.numdatapoints
                #find new std deviatin using variance
                self.differencestdeviation = math.sqrt(self.differencevariance)
                self.logger.info("difference is %d, aftertick, new difference mean is %d, new std deviation is %d", difference, self.differencemean, self.differencestdeviation)
            else:
                self.differencemean = (self.differencemean * (DISTRIBUTION_MEMORY) - self.differencetracker[self.numdatapoints%DISTRIBUTION_MEMORY] + difference) / DISTRIBUTION_MEMORY
                self.differencevariance = (self.differencevariance * (DISTRIBUTION_MEMORY) - self.differencetracker[self.numdatapoints%DISTRIBUTION_MEMORY]**2 + difference**2) / DISTRIBUTION_MEMORY
                self.differencestdeviation = math.sqrt(self.differencevariance)
                self.logger.info("WE are now in rolling zone, difference is %d, aftertick, new difference mean is %d, new std deviation is %d", difference, self.differencemean, self.differencestdeviation)
            self.differencetracker[self.numdatapoints%DISTRIBUTION_MEMORY] = difference

        #set data level to 30
        #attempt trade on mean + 1 standar deviation
        if self.numdatapoints > 30:
            #trade
            if self.etfprice - self.futureprice > self.differencemean + self.differencestdeviation and self.position - self.activesell >= -POSITION_LIMIT+11 and self.activevolume < 190:
                #sell etf
                self.ask_id = next(self.order_ids)
                #self.ask_price = new_ask_price
                self.send_insert_order(self.ask_id, Side.SELL, self.etfaskprice - TICK_SIZE_IN_CENTS, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.activevolume += 10
                self.activesell +=10
                self.asks.add(self.ask_id)

            elif self.etfprice - self.futureprice < self.differencemean - self.differencestdeviation and self.position + self.activebuy <= POSITION_LIMIT-11 and self.activevolume < 190:
                #buy etf
                self.bid_id = next(self.order_ids)
                #self.bid_price = new_bid_price
                self.send_insert_order(self.bid_id, Side.BUY, self.etfbidprice + TICK_SIZE_IN_CENTS, LOT_SIZE, Lifespan.GOOD_FOR_DAY)
                self.activevolume += 10
                self.activebuy += 10
                self.bids.add(self.bid_id)

        #if we make moneyu over .04 percent, we buy and hedge 
        # amount we buy depends on standard deviations away from mean
        # furhter optimization we passive order the hedge? or too slow too much risk

        #add buy mechanism
        #review hedge mechanism
        #


        #clear old orders
        #order count limit on top of volume?
