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

from typing import List

from ready_trader_go import BaseAutoTrader, Instrument, Lifespan, MAXIMUM_ASK, MINIMUM_BID, Side

#to improve
#if none to match create ur own?
#if below spreadlimit, switch to arbitrage?
#set tiers, match if above limit? if within limit ignore? stick to own limit?
#undercut if volume at particular levle is more than double (or volume over 800?) and spread is still large



LOT_SIZE = 10
POSITION_LIMIT = 100
TICK_SIZE_IN_CENTS = 100
MIN_BID_NEAREST_TICK = (MINIMUM_BID + TICK_SIZE_IN_CENTS) // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS
MAX_ASK_NEAREST_TICK = MAXIMUM_ASK // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS

TRADESPREAD_LIMIT = 400


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

        #track prices and volumes of orderbook
        self.etfaskprices = []
        self.etfbidprices = []
        self.etfaskvolumes = []
        self.etfbidvolumes = []
        self.tier1spread = 0
        self.tier1weight = 0

        #future very liquid doesnt matter
        self.futureaskprice = 0
        self.futurebidprice = 0

        self.tier1bid = [0,0, 0]      #money making bid offer (match market) :[price, volume, order_id]
        self.tier1ask = [0,0, 0]      #meney making ask offer (match market)  :[price, volume, order_id]

        #tier 2 spread, greedily choose least volume until we reach tradespreadlimit (only if 1 is too low)
        #has a penalty value attatched, (volume within spread)
        #we use penalty value adn std deviation to decide wether to arbitrage or use tier 2 spread
        #dont even need tier 2, all tier 1, add weight to penalty

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

    def on_order_book_update_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                                     ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        """Called periodically to report the status of an order book.

        The sequence number can be used to detect missed or out-of-order
        messages. The five best available ask (i.e. sell) and bid (i.e. buy)
        prices are reported along with the volume available at each of those
        price levels.
        """
        self.logger.info("received order book for instrument %d with sequence number %d", instrument,
                         sequence_number)
        
        #record etf data
        if instrument == Instrument.FUTURE:
            self.futureaskprice = ask_prices[0]
            self.futurebidprice = bid_prices[0]
        elif instrument == Instrument.ETF:
            self.etfaskprices = ask_prices
            self.etfbidprices = bid_prices
            self.etfaskvolumes = ask_volumes
            self.etfbidvolumes = bid_volumes
            self.tier1spread = self.etfaskprices[0] - self.etfbidprices[0]

            #we market make on the etf
            #check for 0s in ask and bid prices,
            #undercut if wide enough, match if not, go to next level if too narrow?

            #use to determine bid and ask price
            

            #for now we are looking only at edges, and using full, cancel old, set new
            if True:
                #avoid math errors (etf breaches), cancel both first
                if self.etfaskprices[0] != self.tier1ask[0] and 100+self.position!=0:
                    if self.tier1ask[2] != 0:
                        self.send_cancel_order(self.tier1ask[2])
                        self.tier1ask[1] = 0
                if self.etfbidprices[0] != self.tier1bid[0] and 100-self.position!=0:
                    if self.tier1bid[2] != 0:
                        self.send_cancel_order(self.tier1bid[2])
                        self.tier1bid[1] = 0

                if self.etfaskprices[0] != self.tier1ask[0] and 100+self.position!=0:
                    self.tier1ask[0] = self.etfaskprices[0]
                    self.ask_id = next(self.order_ids)
                    self.send_insert_order(self.ask_id, Side.SELL, self.tier1ask[0], 100 + self.position, Lifespan.GOOD_FOR_DAY)
                    self.asks.add(self.ask_id)
                    self.tier1ask[2] = self.ask_id
                    self.tier1ask[1] = self.position + 100
                if self.etfbidprices[0] != self.tier1bid[0] and 100-self.position!=0:
                    self.tier1bid[0] = self.etfbidprices[0]
                    self.bid_id = next(self.order_ids)
                    self.send_insert_order(self.bid_id, Side.BUY, self.tier1bid[0], 100 - self.position, Lifespan.GOOD_FOR_DAY)
                    self.bids.add(self.bid_id)
                    self.tier1bid[2] = self.bid_id
                    self.tier1bid[1] = 100 - self.position
            else:
                if self.tier1ask[2] != 0:
                    self.send_cancel_order(self.tier1ask[2])
                    self.tier1ask = [0,0,0]
                if self.tier1bid[2] != 0:
                    self.send_cancel_order(self.tier1bid[2])
                    self.tier1bid = [0,0,0]

            self.logger.info("current sperad is %d, current weight is %d", self.tier1spread, self.tier1weight)

            #if no buyer or no seller, set own spread,
            #if no both, set around etf price





        


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
        if client_order_id in self.bids:
            self.position += volume
            self.send_hedge_order(next(self.order_ids), Side.ASK, MIN_BID_NEAREST_TICK, volume)
        elif client_order_id in self.asks:
            self.position -= volume
            self.send_hedge_order(next(self.order_ids), Side.BID, MAX_ASK_NEAREST_TICK, volume)

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
        if client_order_id == self.tier1ask[2]:
            self.tier1ask[1] = remaining_volume
        elif client_order_id == self.tier1bid[2]:
            self.tier1bid[1] = remaining_volume   


    def on_trade_ticks_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                               ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        """Called periodically when there is trading activity on the market.

        The five best ask (i.e. sell) and bid (i.e. buy) prices at which there
        has been trading activity are reported along with the aggregated volume
        traded at each of those price levels.

        If there are less than five prices on a side, then zeros will appear at
        the end of both the prices and volumes arrays.
        """

        #if we are below trade spread limit, switch to arbitrage
        self.logger.info("received trade ticks for instrument %d with sequence number %d", instrument,
                         sequence_number)
