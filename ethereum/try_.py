#!/usr/bin/env python3

from pyweb3 import w3, utils, web3, eth_abi, wrap_neterrs

import abi
import db
import dex.uniswapv2

# filters can be polled synchronously or asynchronously, see web3py docs
# filters only work on local nodes
#    daicontract.events.Transfer.createFilter(fromBlock='latest').get_all_entries()
# it looks like filters are likely to work if a contract is made with no address
# but it's possible work with the internals may be needed (the log_entry_formatter property)
#    if events that don't match the abi throw an error, halting filtering

# getLogs works on remote and local nodes, but appears to need a contract address

usv2 = dex.uniswapv2.dex()

for pair in usv2.pairs():
    print(pair.db.index, pair.db)
    for tx in pair.logs():
        print(tx)
db.c.commit()
