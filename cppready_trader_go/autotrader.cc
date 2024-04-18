// Copyright 2021 Optiver Asia Pacific Pty. Ltd.
//
// This file is part of Ready Trader Go.
//
//     Ready Trader Go is free software: you can redistribute it and/or
//     modify it under the terms of the GNU Affero General Public License
//     as published by the Free Software Foundation, either version 3 of
//     the License, or (at your option) any later version.
//
//     Ready Trader Go is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU Affero General Public License for more details.
//
//     You should have received a copy of the GNU Affero General Public
//     License along with Ready Trader Go.  If not, see
//     <https://www.gnu.org/licenses/>.
#include <array>

#include <boost/asio/io_context.hpp>

#include <ready_trader_go/logging.h>

#include "autotrader.h"

using namespace ReadyTraderGo;

RTG_INLINE_GLOBAL_LOGGER_WITH_CHANNEL(LG_AT, "AUTO")

//constexpr int LOT_SIZE = 10;
//constexpr int POSITION_LIMIT = 100;
constexpr int TICK_SIZE_IN_CENTS = 100;
constexpr int MIN_BID_NEARST_TICK = (MINIMUM_BID + TICK_SIZE_IN_CENTS) / TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS;
constexpr int MAX_ASK_NEAREST_TICK = MAXIMUM_ASK / TICK_SIZE_IN_CENTS * TICK_SIZE_IN_CENTS;

//constexpr int TRADESPREAD_LIMIT = 600
//inside functionnow

AutoTrader::AutoTrader(boost::asio::io_context& context) : BaseAutoTrader(context)
{
}

void AutoTrader::DisconnectHandler()
{
    BaseAutoTrader::DisconnectHandler();
    RLOG(LG_AT, LogLevel::LL_INFO) << "execution connection lost";
}

void AutoTrader::ErrorMessageHandler(unsigned long clientOrderId,
                                     const std::string& errorMessage)
{
    RLOG(LG_AT, LogLevel::LL_INFO) << "error with order " << clientOrderId << ": " << errorMessage;
    if (clientOrderId != 0 && ((self_asks.count(clientOrderId) == 1) || (self_bids.count(clientOrderId) == 1)))
    {
        OrderStatusMessageHandler(clientOrderId, 0, 0, 0);
    }
}

void AutoTrader::HedgeFilledMessageHandler(unsigned long clientOrderId,
                                           unsigned long price,
                                           unsigned long volume)
{
    RLOG(LG_AT, LogLevel::LL_INFO) << "hedge order " << clientOrderId << " filled for " << volume
                                   << " lots at $" << price << " average price in cents";
}

void AutoTrader::OrderBookMessageHandler(Instrument instrument,
                                         unsigned long sequenceNumber,
                                         const std::array<unsigned long, TOP_LEVEL_COUNT>& askPrices,
                                         const std::array<unsigned long, TOP_LEVEL_COUNT>& askVolumes,
                                         const std::array<unsigned long, TOP_LEVEL_COUNT>& bidPrices,
                                         const std::array<unsigned long, TOP_LEVEL_COUNT>& bidVolumes)
{
    if (instrument == Instrument::ETF) {
        unsigned long new_ask = 0;
        unsigned long new_bid = 0;
        unsigned long askdepth = 0;
        unsigned long biddepth = 0;

        const int spread = 600;
        const int tick = TICK_SIZE_IN_CENTS;

        self_halt = false;
        while(true){
            if (askPrices[askdepth] == 0 && bidPrices[biddepth] == 0){
                self_halt = true;
                break;
            } else if (askPrices[askdepth] == 0){
                new_ask = bidPrices[biddepth] + spread;
                new_bid = bidPrices[biddepth];
                break;
            } else if (bidPrices[biddepth] == 0){
                new_bid = askPrices[askdepth] - spread;
                new_ask = askPrices[askdepth];
                break;
            }

            signed long currentspread = askPrices[askdepth] - bidPrices[biddepth];
            if (currentspread > spread + tick * 2){
                new_ask = askPrices[askdepth] - tick;
                new_bid = bidPrices[biddepth] + tick;
                break;
            } else if (currentspread > spread + tick || currentspread == spread){
                if (askVolumes[askdepth] > bidVolumes[biddepth]) {
                    new_ask = askPrices[askdepth] - tick;
                    new_bid = bidPrices[biddepth];
                    break;
                } else {
                    new_ask = askPrices[askdepth];
                    new_bid = bidPrices[biddepth] + tick;
                    break;
                }
            } else {
                if (askVolumes[askdepth] > bidVolumes[biddepth] && biddepth != 4){
                    biddepth ++;
                } else if (askVolumes[askdepth] <= bidVolumes[biddepth] && askdepth !=4){
                    askdepth ++;
                } else if (biddepth == 4 && askdepth != 4){
                    askdepth++;
                } else if (askdepth == 4 && biddepth != 4){
                    biddepth++;
                } else {
                    self_halt = true;
                    break;
                }
            }
        }

        if (self_buyvolume > 200 || self_soldvolume > 200){
            if (self_soldvolume > 2 * self_buyvolume){
                new_ask += tick;
                new_bid += tick;
            } else if(self_buyvolume > 2 * self_soldvolume){
                new_ask -= tick;
                new_bid -= tick;
            }
        }

        if (self_halt == false) {
            if (new_ask!=self_tier1ask[0]){
                SendCancelOrder(self_tier1ask[2]);
                self_resetask = self_tier1ask[2];
                self_tier1ask[1] = 0;
                self_tier1ask[2] = 0;
            }
            if (new_bid != self_tier1bid[0]){
                SendCancelOrder(self_tier1bid[2]);
                self_resetbid = self_tier1bid[2];
                self_tier1bid[1] = 0;
                self_tier1bid[2] = 0;
            }

            if (new_ask != self_tier1ask[0] && 100 + self_position != 0 && self_resetask == 0){
                self_tier1ask[0] = new_ask;
                self_order_ids++;
                self_ask_id = self_order_ids;
                SendInsertOrder(self_ask_id, Side::SELL, self_tier1ask[0], 100+self_position, Lifespan::GOOD_FOR_DAY);
                self_asks.emplace(self_ask_id);
                self_tier1ask[2] = self_ask_id;
                self_tier1ask[1] = self_position + 100;
            } 
            if (new_bid != self_tier1bid[0] && 100 - self_position != 0 && self_resetbid == 0){
                self_tier1bid[0] = new_bid;
                self_order_ids++;
                self_bid_id = self_order_ids;
                SendInsertOrder(self_bid_id, Side::BUY, self_tier1bid[0], 100 - self_position, Lifespan::GOOD_FOR_DAY);
                self_bids.emplace(self_bid_id);
                self_tier1bid[2] = self_bid_id;
                self_tier1bid[1] = 100 - self_position;
            }

            self_tier1ask[0] = new_ask;
            self_tier1bid[0] = new_bid;
        } else {
            if (self_tier1ask[2]!= 0){
                SendCancelOrder(self_tier1ask[2]);
                self_tier1ask[0] = 0;
                self_tier1ask[1] = 0;
                self_tier1ask[2] = 0;
                self_resetask = 0;
            }
            if (self_tier1bid[2] != 0){
                SendCancelOrder(self_tier1bid[2]);
                self_tier1bid[0] = 0;
                self_tier1bid[1] = 0;
                self_tier1bid[2] = 0;
                self_resetbid = 0;
            }
        }
        self_soldvolume = 0;
        self_buyvolume = 0;
    }
    
    //logs go to the end
    RLOG(LG_AT, LogLevel::LL_INFO) << "order book received for " << instrument << " instrument"
                                   << ": ask prices: " << askPrices[0]
                                   << "; ask volumes: " << askVolumes[0]
                                   << "; bid prices: " << bidPrices[0]
                                   << "; bid volumes: " << bidVolumes[0];
}

void AutoTrader::OrderFilledMessageHandler(unsigned long clientOrderId,
                                           unsigned long price,
                                           unsigned long volume)
{
    if (self_asks.count(clientOrderId) > 0)
    {
        self_position -= (long)volume;
        SendHedgeOrder(self_order_ids++, Side::BUY, MAX_ASK_NEAREST_TICK, volume);
    }
    else if (self_bids.count(clientOrderId) > 0)
    {
        self_position += (long)volume;
        SendHedgeOrder(self_order_ids++, Side::SELL, MIN_BID_NEARST_TICK, volume);
    }
    RLOG(LG_AT, LogLevel::LL_INFO) << "order " << clientOrderId << " filled for " << volume
                               << " lots at $" << price << " cents";
}

void AutoTrader::OrderStatusMessageHandler(unsigned long clientOrderId,
                                           unsigned long fillVolume,
                                           unsigned long remainingVolume,
                                           signed long fees)
{
    if (remainingVolume == 0)
    {
        if (clientOrderId == self_ask_id)
        {
            self_ask_id = 0;
        }
        else if (clientOrderId == self_bid_id)
        {
            self_bid_id = 0;
        }

        if (clientOrderId == self_resetask){
            if (self_halt == false && 100 + self_position != 0){
                self_order_ids++;
                self_ask_id = self_order_ids;
                SendInsertOrder(self_ask_id, Side::SELL, self_tier1ask[0], 100+self_position, Lifespan::GOOD_FOR_DAY);
                self_asks.emplace(self_ask_id);
                self_tier1ask[2] = self_ask_id;
                self_tier1ask[1] = self_position + 100;
            }
        } else if (clientOrderId == self_resetbid){
            if (self_halt == false && 100 - self_position != 0){
                self_order_ids++;
                self_bid_id = self_order_ids;
                SendInsertOrder(self_bid_id, Side::BUY, self_tier1bid[0], 100 - self_position, Lifespan::GOOD_FOR_DAY);
                self_bids.emplace(self_bid_id);
                self_tier1bid[2] = self_bid_id;
                self_tier1bid[1] = 100 - self_position;
            }
        }
        self_asks.erase(clientOrderId);
        self_bids.erase(clientOrderId);
    }
    if (clientOrderId == self_tier1ask[2]){
        self_tier1ask[1] = remainingVolume;
    } else if (clientOrderId == self_tier1bid[2]){
        self_tier1bid[1] = remainingVolume;
    }
}

void AutoTrader::TradeTicksMessageHandler(Instrument instrument,
                                          unsigned long sequenceNumber,
                                          const std::array<unsigned long, TOP_LEVEL_COUNT>& askPrices,
                                          const std::array<unsigned long, TOP_LEVEL_COUNT>& askVolumes,
                                          const std::array<unsigned long, TOP_LEVEL_COUNT>& bidPrices,
                                          const std::array<unsigned long, TOP_LEVEL_COUNT>& bidVolumes)
{
    if (instrument == Instrument::ETF){
        self_buyvolume += bidVolumes[0] + bidVolumes[1] + bidVolumes[2] + bidVolumes[3] + bidVolumes[4];
        self_soldvolume += askVolumes[0] + askVolumes[1] + askVolumes[2] + askVolumes[3] + askVolumes[4];
    }
    
    RLOG(LG_AT, LogLevel::LL_INFO) << "trade ticks received for " << instrument << " instrument"
                                   << ": ask prices: " << askPrices[0]
                                   << "; ask volumes: " << askVolumes[0]
                                   << "; bid prices: " << bidPrices[0]
                                   << "; bid volumes: " << bidVolumes[0];
}
