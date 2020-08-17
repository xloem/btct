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
from bitsharesbase.operations import getOperationClassForId,getOperationNameForId

log = logging.getLogger("grapheneapi")
log.setLevel(logging.DEBUG)

bitshares = BitShares(node="wss://node.bitshares.eu", num_retries=-1)
bitshares.connect()

#def get_all_assets():
#    assets = {}
#    lastAsset = None
#    while True:
#        asset_chunk = bitshares.rpc.list_assets(lastAsset,64)
#        if 1 >= len(asset_chunk):
#            break
#        for asset in asset_chunk:
#            assets[asset['symbol']] = asset
#        lastAsset = asset_chunk[-1]

markets = {}

def on_tx(data):
    #print(data)
    for operation in data["operations"]:
        if getOperationNameForId(operation[0]) == 'limit_order_create':
            base = operation[1]['amount_to_sell']['asset_id']
            quote = operation[1]['min_to_receive']['asset_id']
            if base > quote:
                base, quote = quote, base
            basequote = base + '/' + quote
            if not basequote in markets:
                market = Market(basequote, blockchain_instance=bitshares)
                markets[basequote] = market

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

                # default ranges:
                # stop = datetime.now()
                # start = stop - timedelta(hours=24)
                history = market.trades(limit=25,start=None,stop=None)
                for trade in history:
                    print(trade)

notify = Notify(bitshares=bitshares, markets=list(), on_tx=on_tx)
notify.listen()



block=bitshares.rpc.get_block(1)
print(block)

market = Market("BTC:BTS", blockchain_instance=bitshares)

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
