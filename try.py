#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging

from bitshares import BitShares
from bitshares.asset import Asset
from bitshares.amount import Amount
from bitshares.account import Account
from bitshares.price import Price, Order
from bitshares.market import Market
from bitshares.notify import Notify

log = logging.getLogger("grapheneapi")
log.setLevel(logging.DEBUG)

bitshares = BitShares(node="wss://node.bitshares.eu", num_retries=-1)
bitshares.connect()

def get_all_assets():
    assets = {}
    lastAsset = None
    while True:
        asset_chunk = bitshares.rpc.list_assets(lastAsset,64)
        if 1 >= len(asset_chunk):
            break
        for asset in asset_chunk:
            assets[asset['symbol']] = asset
        lastAsset = asset_chunk[-1]

def on_block(data):
    print(data)

notify = Notify(bitshares=bitshars, markets=list(), on_block=on_block)
notify.listen()



block=bitshares.rpc.get_block(1)
print(block)

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
