#!/usr/bin/env python3

from pyweb3 import w3, utils, web3, eth_abi, wrap_neterrs

import abi
import db
    

uniswapv2 = db.dex(abi.uniswapv2_factory_addr, 'UNI-V2')

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

#for pair in uniswapv2ct.events.PairCreated().getLogs(fromBlock=w3.eth.block_number-126):#tailblock-127,toBlock=tailblock):
firstpairidx = 0
for row in db.pair(dex=uniswapv2).descending('index'):
    #print(row)
    firstpairidx = row.index + 1
    break
for pairidx in range(firstpairidx, wrap_neterrs(uniswapv2ct.functions.allPairsLength())):
    pairaddr = wrap_neterrs(uniswapv2ct.functions.allPairs(pairidx))
    pairct = w3.eth.contract(address=pairaddr, abi=abi.uniswapv2_pair)
    tokenaddrs = (wrap_neterrs(pairct.functions.token0()), wrap_neterrs(pairct.functions.token1()))
    symbols = ['','']
    for tokenidx in range(2):
        try:
            symbols[tokenidx]=wrap_neterrs(w3.eth.contract(address=tokenaddrs[tokenidx], abi=abi.uniswapv2_erc20).functions.symbol())
        except Exception as e: # this absorbs keyboard-interrupt, put error type in? .. the error is thrown from an underlying issue in the library, resulting from calling to the wrong spec.  other errors could be thrown, add 'em I guess.
            if isinstance(e, OverflowError) or isinstance(e, web3.exceptions.ContractLogicError):
                print('pairidx',pairidx,'token',tokenidx,tokenaddrs[tokenidx],'raised an erc20 error')
                symbols[tokenidx] = tokenaddrs[tokenidx]
            else:
                raise e
    [db.token.ensure(addr, symbol) for addr, symbol in zip(tokenaddrs, symbols)]
    print(pairidx, db.pair(pairaddr, tokenaddrs[0], tokenaddrs[1], uniswapv2, index=pairidx))
#for token0 in db.token:
#    for token1 in db.token:
#        pair = uniswapv2ct.
db.c.commit()

daicontract = w3.eth.contract(address=dai.addr,abi=abi.erc20)
somelogs = daicontract.events.Transfer().getLogs(fromBlock=daicontract.web3.eth.block_number-127,toBlock='latest')


