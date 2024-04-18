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


LOT_SIZE = 10
POSITION_LIMIT = 100
TICK_SIZE_IN_CENTS = 100
MIN_BID_NEAREST_TICK = (MINIMUM_BID + TICK_SIZE_IN_CENTS) // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS
MAX_ASK_NEAREST_TICK = MAXIMUM_ASK // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS

#hedge in increments , every tick

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
        self.position = 0
        self.hedgeposition = 0
        self.emergencyhedgecounter = 0
        self.hedgeasks = set()
        self.hedgebids = set()

        # self.soldvolume = 0
        # self.buyvolume = 0
        self.halt = False

        self.resetask = 0
        self.resetbid = 0

        self.tier1bid = [0,0, 0]      #money making bid offer (match market) :[price, volume, order_id]
        self.tier1ask = [0,0, 0]      #meney making ask offer (match market)  :[price, volume, order_id]



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

        if client_order_id in self.hedgeasks:
            self.hedgeposition -= volume
        elif client_order_id in self.hedgebids:
            self.hedgeposition +=volume
        self.bids.discard(client_order_id)
        self.asks.discard(client_order_id)
        if self.hedgeposition == -self.position:
            self.emergencyhedgecounter = 0
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

        
        if instrument == Instrument.ETF:
            #we market make on the etf
            new_ask = 0
            new_bid = 0
            askdepth = 0
            biddepth = 0

            spread = 700 #TRADESPREAD_LIMIT
            tick = 100 #TICK_SIZE_IN_CENTS

            halt = False      
            while 1:
                #check for 0s
                if ask_prices[askdepth] == 0 and bid_prices[biddepth] == 0:
                    halt = True
                    break
                elif ask_prices[askdepth] == 0:
                    new_ask = bid_prices[biddepth] + spread
                    new_bid = bid_prices[biddepth]
                    break
                elif bid_prices[biddepth] == 0:
                    new_bid = ask_prices[askdepth] - spread
                    new_ask = ask_prices[askdepth]
                    break
                
                currentspread = ask_prices[askdepth] - bid_prices[biddepth]
                if currentspread > spread + tick*2:
                    new_ask = ask_prices[askdepth] - tick
                    new_bid = bid_prices[biddepth] + tick
                    break
                elif currentspread > spread + tick or currentspread == spread:                  #equals shifts out for now
                    if ask_volumes[askdepth] > bid_volumes[biddepth]:
                        new_ask = ask_prices[askdepth] - tick
                        new_bid = bid_prices[biddepth]
                        break
                    else:
                        new_ask = ask_prices[askdepth]
                        new_bid = bid_prices[biddepth] + tick
                        break

                #otherwise trade spread is too small, go to next depth depending on weight
                else:
                    if ask_volumes[askdepth] > bid_volumes[biddepth] and biddepth != 4:
                        biddepth += 1
                    elif ask_volumes[askdepth] <= bid_volumes[biddepth] and askdepth != 4:
                        askdepth += 1
                    elif biddepth ==4 and askdepth !=4:
                        askdepth += 1
                    elif askdepth ==4 and biddepth !=4: 
                        biddepth += 1
                    else:
                        self.logger.info("no more data, this shouldnt happen error error")
                        halt = True
                        break

            #no tick adjust test
            # if self.buyvolume > 200 or self.soldvolume > 200:
            #     if self.soldvolume > 2* self.buyvolume:
            #         new_ask += tick
            #         new_bid +=tick
            #         #self.logger.info("upshift here")
            #     elif self.buyvolume > 2* self.soldvolume:
            #         new_ask-=tick
            #         new_bid -= tick
            #         #self.logger.info("downshift here")

            #for now we are looking only at edges, and using full, cancel old, set new
            if halt == False:                                                         #dont run if  prices are 0 0 !!!!!
                #avoid math errors (etf breaches), cancel both first
                if new_ask != self.tier1ask[0]:# and 100+self.position!=0:
                    #if self.tier1ask[2] != 0:
                    self.send_cancel_order(self.tier1ask[2])
                    self.resetask = self.tier1ask[2]
                    self.tier1ask[1] = 0
                    #self.logger.info("cancelled order ask %d", self.tier1ask[2])               #REMOVE LOGGER
                    self.tier1ask[2] = 0
                if new_bid != self.tier1bid[0]:# and 100-self.position!=0:
                    #if self.tier1bid[2] != 0:
                    self.send_cancel_order(self.tier1bid[2])
                    self.resetbid = self.tier1bid[2]
                    self.tier1bid[1] = 0
                    #self.logger.info("cancelled order bid %d", self.tier1bid[2])                #BUG NUMBER 5 DOESNT CANCEL  Caused by order filled coming in late, fixed by removing position condition, cancel anywasy
                    self.tier1bid[2] = 0

                #we move trading to after confirmation of bids

                #but we must do the first bid here
                if  self.resetask == 0 and new_ask != self.tier1ask[0] and 100+self.position!=0:
                    ask_id = next(self.order_ids)
                    self.send_insert_order(ask_id, Side.SELL, new_ask, min(72, 100 + self.position), Lifespan.GOOD_FOR_DAY)
                    self.tier1ask[0] = new_ask
                    #self.logger.info("sold order %d", self.ask_id)
                    self.asks.add(ask_id)
                    self.tier1ask[2] = ask_id
                    self.tier1ask[1] = min(72, self.position + 100)
                if self.resetbid == 0 and new_bid != self.tier1bid[0] and 100-self.position!=0:
                    bid_id = next(self.order_ids)
                    self.send_insert_order(bid_id, Side.BUY, new_bid, min(72, 100 - self.position), Lifespan.GOOD_FOR_DAY)
                    self.tier1bid[0] = new_bid
                    #self.logger.info("bought order %d", self.bid_id)
                    self.bids.add(bid_id)
                    self.tier1bid[2] = bid_id
                    self.tier1bid[1] = min(72, 100 - self.position)


                #if we receive a cancel from here, (and volume = 0) then we should buy, if statement to check value not needed because it is in cancel
                self.tier1ask[0] = new_ask
                self.tier1bid[0] = new_bid
            
            #cancel if outside of limit (inner weight too high?)(switch to arbitrage?)
            else:       
                if self.tier1ask[2] != 0:
                    self.send_cancel_order(self.tier1ask[2])
                    self.tier1ask = [0,0,0]
                    self.resetask = 0
                if self.tier1bid[2] != 0:
                    self.send_cancel_order(self.tier1bid[2])
                    self.tier1bid = [0,0,0]
                    self.resetbid = 0
                            #record etf data

            self.halt = halt
            # self.soldvolume = 0
            # self.buyvolume = 0
        else:       #we make hedge calls on future orderbook calls
            if self.emergencyhedgecounter > 200:
                if self.hedgeposition < -self.position:
                    bidid = next(self.order_ids)
                    self.send_hedge_order(bidid, Side.BID, MAX_ASK_NEAREST_TICK, -self.position - self.hedgeposition)
                    self.hedgebids.add(bidid)
                else:
                    askid = next(self.order_ids)
                    self.send_hedge_order(askid, Side.ASK, MIN_BID_NEAREST_TICK, self.hedgeposition + self.position)
                    self.hedgeasks.add(askid)
                self.emergencyhedgecounter = 0
            elif self.hedgeposition != -self.position:
                if self.hedgeposition < -self.position:
                    bidid = next(self.order_ids)
                    self.send_hedge_order(bidid, Side.BID, MAX_ASK_NEAREST_TICK, min(-self.position - self.hedgeposition, 1))
                    self.hedgebids.add(bidid)
                else:
                    askid = next(self.order_ids)
                    self.send_hedge_order(askid, Side.ASK, MIN_BID_NEAREST_TICK, min(self.hedgeposition + self.position, 1))
                    self.hedgeasks.add(askid)
                self.emergencyhedgecounter += 1

        self.logger.info("received order book for instrument %d with sequence number %d", instrument,
                         sequence_number)

    def on_order_filled_message(self, client_order_id: int, price: int, volume: int) -> None:
        """Called when one of your orders is filled, partially or fully.

        The price is the price at which the order was (partially) filled,
        which may be better than the order's limit price. The volume is
        the number of lots filled at that price.
        """
        if client_order_id in self.bids:
            self.position += volume
            #self.send_hedge_order(next(self.order_ids), Side.ASK, MIN_BID_NEAREST_TICK, volume)
        elif client_order_id in self.asks:
            self.position -= volume
            #self.send_hedge_order(next(self.order_ids), Side.BID, MAX_ASK_NEAREST_TICK, volume)
        self.logger.info("received order filled for order %d with price %d and volume %d", client_order_id,
                         price, volume)

    def on_order_status_message(self, client_order_id: int, fill_volume: int, remaining_volume: int,
                                fees: int) -> None:
        """Called when the status of one of your orders changes.

        The fill_volume is the number of lots already traded, remaining_volume
        is the number of lots yet to be traded and fees is the total fees for
        this order. Remember that you pay fees for being a market taker, but
        you receive fees for being a market maker, so fees can be negative.

        If an order is cancelled its remaining volume will be zero.
        """
        if remaining_volume == 0:

            if client_order_id == self.resetask:                #this should fix errors
                if 100+self.position!=0 and self.halt == False:
                    ask_id = next(self.order_ids)
                    self.send_insert_order(ask_id, Side.SELL, self.tier1ask[0], min(72, 100 + self.position), Lifespan.GOOD_FOR_DAY)
                    #self.logger.info("sold order %d", self.ask_id)
                    self.asks.add(ask_id)
                    self.tier1ask[2] = ask_id
                    self.tier1ask[1] = min(72, self.position + 100)
            elif client_order_id == self.resetbid:
                if 100-self.position!=0 and self.halt == False :
                    bid_id = next(self.order_ids)
                    self.send_insert_order(bid_id, Side.BUY, self.tier1bid[0], min(72, 100 - self.position), Lifespan.GOOD_FOR_DAY)
                    #self.logger.info("bought order %d", self.bid_id)
                    self.bids.add(bid_id)
                    self.tier1bid[2] = bid_id
                    self.tier1bid[1] = min(72, 100 - self.position)

            self.bids.discard(client_order_id)
            self.asks.discard(client_order_id)
        if client_order_id == self.tier1ask[2]:                    
            self.tier1ask[1] = remaining_volume
        elif client_order_id == self.tier1bid[2]:
            self.tier1bid[1] = remaining_volume   

        self.logger.info("received order status for order %d with fill volume %d remaining %d and fees %d",
                         client_order_id, fill_volume, remaining_volume, fees)


    def on_trade_ticks_message(self, instrument: int, sequence_number: int, ask_prices: List[int],
                               ask_volumes: List[int], bid_prices: List[int], bid_volumes: List[int]) -> None:
        """Called periodically when there is trading activity on the market.

        The five best ask (i.e. sell) and bid (i.e. buy) prices at which there
        has been trading activity are reported along with the aggregated volume
        traded at each of those price levels.

        If there are less than five prices on a side, then zeros will appear at
        the end of both the prices and volumes arrays.
        """
        # if instrument == Instrument.ETF:
        #     self.buyvolume += sum(bid_volumes)
        #     self.soldvolume += sum(ask_volumes)

        #if we are below trade spread limit, switch to arbitrage
        self.logger.info("received trade ticks for instrument %d with sequence number %d", instrument,
                         sequence_number)
