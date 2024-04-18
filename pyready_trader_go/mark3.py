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


#to improve, at even to tradespread, undercut one? maintain spread limit?
#add arbitrage mode, full arbitrager
#test independent full arbitrger first?
#arbitrage for heavy penalty?
#test spread limits 600 and 500?
#TEST NEW DATA SETS NOT JUST NUMBER 1
#spread limit changes with market movement speed!!! mean std of changes perhaps
#theres is technically a bug somewhere (etf puchase limit breached)




LOT_SIZE = 10
POSITION_LIMIT = 100
TICK_SIZE_IN_CENTS = 100
MIN_BID_NEAREST_TICK = (MINIMUM_BID + TICK_SIZE_IN_CENTS) // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS
MAX_ASK_NEAREST_TICK = MAXIMUM_ASK // TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS

TRADESPREAD_LIMIT = 600
#SMALLER TRADESPREAD LIMIT LEADS TO BUG
#breach etf limit
#the smaller the more frequent

#in this iteration we adjust when the close bid volume is high, or ask volume is high
#use purchase volumes not bid volume



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
        #self.tier1spread = 0                #dont need spread because you can caluclate it urself
        self.soldvolume = 0
        self.buyvolume = 0
        self.halt = False

        #future very liquid doesnt matter
        self.futureaskprice = 0
        self.futurebidprice = 0

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
            #check for 0s in ask and bid prices,
            #undercut if wide enough, match if not, go to next level if too narrow?

            #use to determine bid and ask price
            new_ask = 0
            new_bid = 0
            askdepth = 0
            biddepth = 0
            #askw = 0            #ask and bid weights
            #bidw = 0
            #NO GLOBALS FOR SPEED?
            spread = TRADESPREAD_LIMIT
            tick = TICK_SIZE_IN_CENTS

            self.halt = False          #no arbitrage mode rn
            while True:
                #check for 0s
                if ask_prices[askdepth] == 0 and bid_prices[biddepth] == 0:
                    self.halt = True
                    break
                elif ask_prices[askdepth] == 0:
                    new_ask = bid_prices[biddepth] + spread
                    break
                elif bid_prices[biddepth] == 0:
                    new_bid = ask_prices[askdepth] - spread
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
                        #bidw += bid_volumes[biddepth]
                        break
                    else:
                        new_ask = ask_prices[askdepth]
                        new_bid = bid_prices[biddepth] + tick
                        #askw += ask_volumes[askdepth]
                        break
                # elif currentspread == spread:
                #     new_ask = ask_prices[askdepth]
                #     new_bid = bid_prices[biddepth]
                #     weight += bid_volumes[biddepth] + ask_volumes[askdepth]                                     #shift out of heavy frame?????????
                #     break

                #otherwise trade spread is too small, go to next depth depending on weight
                else:
                    if ask_volumes[askdepth] > bid_volumes[biddepth] and biddepth != 4:
                        biddepth += 1
                        #bidw += bid_volumes[biddepth-1]
                    elif ask_volumes[askdepth] <= bid_volumes[biddepth] and askdepth != 4:
                        askdepth += 1
                        #askw += ask_volumes[askdepth-1]
                    elif biddepth ==4 and askdepth !=4:
                        askdepth += 1
                        #askw += ask_volumes[askdepth-1]
                    elif askdepth ==4 and biddepth !=4: 
                        biddepth += 1
                        #bidw += bid_volumes[biddepth-1]
                    else:
                        self.logger.info("no more data, this shouldnt happen error error")
                        self.halt = True
                        break
            #self.askweight = askw
            #self.bidweight = bidw
            #idk formula
            #self.logger.info("buy volume: %d, sell volume: %d", self.buyvolume, self.soldvolume)
            if self.buyvolume > 200 or self.soldvolume > 200:
                if self.soldvolume > 2* self.buyvolume:
                    new_ask += tick
                    new_bid +=tick
                    self.logger.info("upshift here")
                elif self.buyvolume > 2* self.soldvolume:
                    new_ask-=tick
                    new_bid -= tick
                    self.logger.info("downshift here")

            #for now we are looking only at edges, and using full, cancel old, set new
            if self.halt == False:                                                         #dont run if  prices are 0 0 !!!!!
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
                if new_ask != self.tier1ask[0] and 100+self.position!=0 and self.resetask == 0:
                    self.tier1ask[0] = new_ask
                    self.ask_id = next(self.order_ids)
                    self.send_insert_order(self.ask_id, Side.SELL, self.tier1ask[0], 100 + self.position, Lifespan.GOOD_FOR_DAY)
                    #self.logger.info("sold order %d", self.ask_id)
                    self.asks.add(self.ask_id)
                    self.tier1ask[2] = self.ask_id
                    self.tier1ask[1] = self.position + 100
                if new_bid != self.tier1bid[0] and 100-self.position!=0 and self.resetbid == 0:
                    self.tier1bid[0] = new_bid
                    self.bid_id = next(self.order_ids)
                    self.send_insert_order(self.bid_id, Side.BUY, self.tier1bid[0], 100 - self.position, Lifespan.GOOD_FOR_DAY)
                    #self.logger.info("bought order %d", self.bid_id)
                    self.bids.add(self.bid_id)
                    self.tier1bid[2] = self.bid_id
                    self.tier1bid[1] = 100 - self.position


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

            #use ask price and bid price, do this calculation after since it is slower
            #reset for next cycle
            self.soldvolume = 0
            self.buyvolume = 0
            self.etfaskprices = ask_prices
            self.etfbidprices = bid_prices
            self.etfaskvolumes = ask_volumes
            self.etfbidvolumes = bid_volumes
            #self.logger.info("current spread is %d", self.tier1ask[0] - self.tier1bid[0])
        elif instrument == Instrument.FUTURE:
            self.futureaskprice = ask_prices[0]
            self.futurebidprice = bid_prices[0]


            #if no buyer or no seller, set own spread,
            #if no both, set around etf price
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
            self.send_hedge_order(next(self.order_ids), Side.ASK, MIN_BID_NEAREST_TICK, volume)
            # if client_order_id != self.tier1bid[2]:
            #     self.send_cancel_order(self.tier1bid[2])                                    #hack fix for over etf bug when order filled is called during orderbook
            #     self.tier1bid = [0,0,0]
        elif client_order_id in self.asks:
            self.position -= volume
            self.send_hedge_order(next(self.order_ids), Side.BID, MAX_ASK_NEAREST_TICK, volume)
            # if client_order_id != self.tier1ask[2]:
            #     self.send_cancel_order(self.tier1ask[2])                                    #hack fix for over etf bug when order filled is called during orderbook
            #     self.tier1ask = [0,0,0]
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
            if client_order_id == self.bid_id:
                self.bid_id = 0
            elif client_order_id == self.ask_id:
                self.ask_id = 0

            if client_order_id == self.resetask:                #this should fix errors
                if self.halt == False and 100+self.position!=0:
                    self.ask_id = next(self.order_ids)
                    self.send_insert_order(self.ask_id, Side.SELL, self.tier1ask[0], 100 + self.position, Lifespan.GOOD_FOR_DAY)
                    #self.logger.info("sold order %d", self.ask_id)
                    self.asks.add(self.ask_id)
                    self.tier1ask[2] = self.ask_id
                    self.tier1ask[1] = self.position + 100
            elif client_order_id == self.resetbid:
                if self.halt == False and 100-self.position!=0:
                    self.bid_id = next(self.order_ids)
                    self.send_insert_order(self.bid_id, Side.BUY, self.tier1bid[0], 100 - self.position, Lifespan.GOOD_FOR_DAY)
                    #self.logger.info("bought order %d", self.bid_id)
                    self.bids.add(self.bid_id)
                    self.tier1bid[2] = self.bid_id
                    self.tier1bid[1] = 100 - self.position

            # It could be either a bid or an ask
            self.bids.discard(client_order_id)
            self.asks.discard(client_order_id)
        if client_order_id == self.tier1ask[2]:                     #change to elif
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
        if instrument == Instrument.ETF:
            self.buyvolume += sum(bid_volumes)
            self.soldvolume += sum(ask_volumes)

        #if we are below trade spread limit, switch to arbitrage
        self.logger.info("received trade ticks for instrument %d with sequence number %d", instrument,
                         sequence_number)
