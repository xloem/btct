#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

from bitshares import BitShares
from bitshares.asset import Asset
from bitshares.amount import Amount
from bitshares.account import Account
from bitshares.price import Price, Order
from bitshares.market import Market

log = logging.getLogger("grapheneapi")
log.setLevel(logging.DEBUG)

bitshares = BitShares(node="wss://node.bitshares.eu", num_retries=-1)
bitshares.connect()

assets = set()
lastAsset = ''
while True:
    asset_chunk = bitshares.rpc.list_assets(lastAsset,50)
    if 1 >= len(asset_chunk):
        break
    asset_chunk = [asset['symbol'] for asset in asset_chunk]
    print(asset_chunk)
    assets |= set(asset_chunk)
    lastAsset = asset_chunk[-1]

market = Market("BTC:BTS", blockchain_instance=bitshares)

print("base=%s\n" % market.get("base"))
print("quote=%s\n" % market.get("quote"))

ticker = market.ticker()
print("lowestAsk=%s\n" % ticker["lowestAsk"])
print("highestBid=%s\n" % ticker["highestBid"])

volume = market.volume24h()
base = market["base"]["symbol"]
quote = market["quote"]["symbol"]

print("volume24h %s=%s" %(base,volume[base]))
print("volume24h %s=%s" %(quote,volume[quote]))

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
