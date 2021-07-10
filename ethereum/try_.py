#!/usr/bin/env python3

from pyweb3 import w3, utils

import abi
import db
    

dai = db.token('0x6B175474E89094C44Da98b954EedeAC495271d0F', 'DAI')
weth = db.token('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'WETH')

uniswapv2 = db.dex(abi.uniswapv2_factory_addr, 'uniswap v2')
db.pair.ensure('0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11', dai, weth, uniswapv2)

# filters can be polled synchronously or asynchronously, see web3py docs
# filters only work on local nodes
#    daicontract.events.Transfer.createFilter(fromBlock='latest').get_all_entries()
# it looks like filters are likely to work if a contract is made with no address
# but it's possible work with the internals may be needed (the log_entry_formatter property)
#    if events that don't match the abi throw an error, halting filtering

# getLogs works on remote and local nodes, but appears to need a contract address

uniswapv2ct = w3.eth.contract(address=abi.uniswapv2_factory_addr,abi=abi.uniswapv2_factory)

# i added this line to debug a strange mismatched abi error.  the line prevents the error =/  quick-workaround
testrecpt = w3.eth.getTransactionReceipt('0xb31fcb852b18303c672b81d90117220624232801ad949bd4047e009eaed73403')
#uniswapv2ct.events.PairCreated()#.processLog(testrecpt.logs[0])

#lasttailblock = w3.eth.block_number
#for tailblock in range(lasttailblock, 0, -127):
for pair in uniswapv2ct.events.PairCreated().getLogs(fromBlock=w3.eth.block_number-126):#tailblock-127,toBlock=tailblock):
    tokenaddrs=(pair.args.token0, pair.args.token1)
    symbols=[w3.eth.contract(address=ta, abi=abi.erc20).functions.symbol().call() for ta in tokenaddrs]
    [db.token.ensure(addr, symbol) for addr, symbol in zip(tokenaddrs, symbols)]
    print(db.pair(pair.args.pair, tokenaddrs[0], tokenaddrs[1], uniswapv2))

daicontract = w3.eth.contract(address=dai.addr,abi=abi.erc20)
somelogs = daicontract.events.Transfer().getLogs(fromBlock=daicontract.web3.eth.block_number-127,toBlock='latest')

