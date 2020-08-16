#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import asyncio

from bitshares.aio import BitShares
from bitshares.aio.asset import Asset
from bitshares.aio.amount import Amount
from bitshares.aio.account import Account
from bitshares.aio.price import Price, Order
from bitshares.aio.market import Market

log = logging.getLogger("grapheneapi")
log.setLevel(logging.DEBUG)

async def main():
    bitshares = BitShares(node="wss://node.bitshares.eu", num_retries=-1)
    await bitshares.connect()

    market = await Market("BTC:BTS", blockchain_instance=bitshares)
    
    print("base=%s\n" % market.get("base"))
    print("quote=%s\n" % market.get("quote"))
    
    ticker = await market.ticker()
    print("lowestAsk=%s\n" % ticker["lowestAsk"])
    print("highestBid=%s\n" % ticker["highestBid"])
    
    volume = await market.volume24h()
    base = market["base"]["symbol"]
    quote = market["quote"]["symbol"]
    
    print("volume24h %s=%s" %(base,volume[base]))
    print("volume24h %s=%s" %(quote,volume[quote]))

asyncio.run(main())


async def test_orderbook(market, place_order):
    orderbook = await market.orderbook()
    assert "bids" in orderbook
    assert "asks" in orderbook
    assert len(orderbook["bids"]) > 0


async def test_get_limit_orders(market, place_order):
    orderbook = await market.get_limit_orders()
    assert len(orderbook) > 0
    assert isinstance(orderbook[0], Order)

async def test_core_quote_market(bitshares, assets, bitasset):
    market = await Market(
        "{}:USD".format(bitasset.symbol), blockchain_instance=bitshares
    )
    await market.core_quote_market()

async def test_core_base_market(bitshares, assets, bitasset):
    market = await Market(
        "USD:{}".format(bitasset.symbol), blockchain_instance=bitshares
    )
    await market.core_base_market()
