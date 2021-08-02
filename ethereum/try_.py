#!/usr/bin/env python3

from pyweb3 import w3, utils, web3, eth_abi, wrap_neterrs

import abi
import db
import dex.uniswapv2

import datetime

# filters can be polled synchronously or asynchronously, see web3py docs
# filters only work on local nodes
#    daicontract.events.Transfer.createFilter(fromBlock='latest').get_all_entries()
# it looks like filters are likely to work if a contract is made with no address
# but it's possible work with the internals may be needed (the log_entry_formatter property)
#    if events that don't match the abi throw an error, halting filtering

# getLogs works on remote and local nodes, but appears to need a contract address

usv2 = dex.uniswapv2.dex()

tokens = usv2.tokens()
for pair in usv2.pairs():
    #print(pair.db.index, pair.db)
    latest_synced_trade = pair.db.latest_synced_trade
    fromBlock = latest_synced_trade.blocknum if latest_synced_trade else 'earliest'
    investment_tup = (10**pair.db.token0.decimals, 10**pair.db.token1.decimals)
    for tx in pair.logs(fromBlock = fromBlock):
        reserves = tx.reserves()
        prices = tx.prices(investment_tup)
        decimals0 = pair.db.token0.decimals - pair.db.token1.decimals
        decimals1 = -decimals0
        prices = (
            (prices[0][0] / 10**decimals0, prices[0][1] / 10**decimals0),
            (prices[1][0] / 10**decimals1, prices[1][1] / 10**decimals1),
        )
        time = datetime.datetime.fromtimestamp(tx.db.block.time).isoformat()
        print(tx.db, time, tx.db.block.addr, prices)
        print(next(tokens))
db.c.commit()
